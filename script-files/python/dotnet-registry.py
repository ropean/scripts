#!/usr/bin/env python3
"""
@title GitHub Package Registry Setup
@description Configure NuGet and NPM to use the moodysanalytics GitHub Packages feed
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Sets up the NuGet source and NPM registry for the moodysanalytics GitHub
Packages feed so that `dotnet` and `npm` can pull private packages.

PAT resolution priority:
    1. --token CLI argument
    2. GITHUB_TOKEN environment variable
    3. Interactive prompt (password-masked)

Exit codes:
    0 - all requested configurations succeeded or already in place
    1 - a required configuration failed

@example
Usage example:
    python dotnet-registry.py                # interactive menu
    python dotnet-registry.py --all          # configure both NuGet and NPM
    python dotnet-registry.py --nuget        # NuGet only
    python dotnet-registry.py --npm          # NPM only
    python dotnet-registry.py --check        # show current status
    python dotnet-registry.py --show-token   # show saved PATs
"""

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

# ── Constants ──────────────────────────────────────────────────────────────────

GITHUB_SOURCE_NAME = "github"
GITHUB_NUGET_URL = "https://nuget.pkg.github.com/moodysanalytics/index.json"
GITHUB_NPM_URL = "https://npm.pkg.github.com"
GITHUB_ORG = "moodysanalytics"
TEST_PACKAGE = "ZMAPI-Windows-X64.Resource"
WIKI_URL = "https://moodysanalytics.atlassian.net/wiki/spaces/CAO/pages/470036157/Connect+to+GitHub+Package+Registry"

# ── Colored output helpers ─────────────────────────────────────────────────────

_NO_COLOR = not sys.stdout.isatty()


def _colored(text: str, code: str) -> str:
    if _NO_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(text: str) -> str:
    return _colored(text, "32")


def yellow(text: str) -> str:
    return _colored(text, "33")


def red(text: str) -> str:
    return _colored(text, "31")


def cyan(text: str) -> str:
    return _colored(text, "36")


def dim(text: str) -> str:
    return _colored(text, "90")


# ── PAT resolution ────────────────────────────────────────────────────────────

_resolved_pat: str | None = None


def resolve_pat(cli_token: str | None) -> str | None:
    """Resolve PAT from CLI arg > env var > interactive prompt. Cached."""
    global _resolved_pat
    if _resolved_pat is not None:
        return _resolved_pat

    if cli_token:
        _resolved_pat = cli_token
        print(dim("  Using PAT from --token argument."))
        return _resolved_pat

    env_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_token:
        _resolved_pat = env_token
        print(dim("  Using PAT from GITHUB_TOKEN environment variable."))
        return _resolved_pat

    print()
    print("  A GitHub Personal Access Token (PAT) with read:packages scope is required.")
    print(f"  See: {cyan(WIKI_URL)}")
    print()
    try:
        pat = getpass.getpass("  Enter your GitHub PAT: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

    if not pat:
        return None

    _resolved_pat = pat
    return _resolved_pat


# ── Subprocess helpers ─────────────────────────────────────────────────────────


def run_cmd(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess:
    # shell=True is required on Windows so that .cmd/.bat wrappers (npm, dotnet) resolve correctly
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=(os.name == "nt"))


# ── NuGet configuration ───────────────────────────────────────────────────────


def _parse_nuget_sources() -> dict[str, bool]:
    """Return {source_name: is_enabled} from `dotnet nuget list source`."""
    result = run_cmd(["dotnet", "nuget", "list", "source"])
    sources: dict[str, bool] = {}
    for line in result.stdout.splitlines():
        # Lines look like:  "  1.  github [Enabled]"  or  "  2.  nuget.org [Disabled]"
        m = re.match(r"\s*\d+\.\s+(.+?)\s+\[(Enabled|Disabled)\]", line)
        if m:
            sources[m.group(1)] = m.group(2) == "Enabled"
    return sources


def _test_nuget_source() -> bool:
    """Return True if a test package search returns at least one version."""
    print(dim(f"  Testing: dotnet package search {TEST_PACKAGE} --source {GITHUB_SOURCE_NAME} ..."))
    try:
        result = run_cmd([
            "dotnet", "package", "search", TEST_PACKAGE,
            "--source", GITHUB_SOURCE_NAME,
            "--exact-match", "--format", "json",
        ], timeout=60)
    except subprocess.TimeoutExpired:
        print(yellow("  Test search timed out."))
        return False

    if result.returncode != 0:
        return False

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return False

    for source in data.get("searchResult", []):
        for pkg in source.get("packages", []):
            if pkg.get("version"):
                return True
    return False


def _add_nuget_source(pat: str) -> bool:
    """Add and authenticate the github NuGet source. Return True on success."""
    print(dim(f"  Adding NuGet source '{GITHUB_SOURCE_NAME}' -> {GITHUB_NUGET_URL}"))
    result = run_cmd([
        "dotnet", "nuget", "add", "source", GITHUB_NUGET_URL,
        "--name", GITHUB_SOURCE_NAME,
    ])
    if result.returncode != 0:
        print(red(f"  Failed to add source: {result.stderr.strip()}"))
        return False

    return _update_nuget_credentials(pat)


def _update_nuget_credentials(pat: str) -> bool:
    """Update credentials for the github NuGet source. Return True on success."""
    print(dim(f"  Updating credentials for source '{GITHUB_SOURCE_NAME}'..."))
    result = run_cmd([
        "dotnet", "nuget", "update", "source", GITHUB_SOURCE_NAME,
        "--username", GITHUB_ORG,
        "--password", pat,
        "--store-password-in-clear-text",
    ])
    if result.returncode != 0:
        print(red(f"  Failed to update credentials: {result.stderr.strip()}"))
        return False
    return True


def configure_nuget(cli_token: str | None) -> bool:
    """Configure the NuGet source for GitHub Packages. Return True on success."""
    print()
    print(cyan("── NuGet Source Configuration ──"))
    print()

    if not shutil.which("dotnet"):
        print(red("  ERROR: 'dotnet' CLI not found. Run dotnet-setup.py first."))
        return False

    sources = _parse_nuget_sources()

    if GITHUB_SOURCE_NAME in sources:
        enabled = sources[GITHUB_SOURCE_NAME]
        if not enabled:
            print(yellow(f"  Source '{GITHUB_SOURCE_NAME}' exists but is disabled. Enabling..."))
            run_cmd(["dotnet", "nuget", "enable", "source", GITHUB_SOURCE_NAME])

        if _test_nuget_source():
            print(green(f"  NuGet source '{GITHUB_SOURCE_NAME}' is configured and working."))
            return True

        # Source exists but test failed — PAT may be expired
        print(yellow(f"  Source '{GITHUB_SOURCE_NAME}' exists but test search returned no results."))
        print(yellow("  Your PAT may be expired or lack read:packages scope."))
        print()
        pat = resolve_pat(cli_token)
        if not pat:
            print(red("  No PAT provided. Cannot reconfigure."))
            return False
        if not _update_nuget_credentials(pat):
            return False
        if _test_nuget_source():
            print(green(f"  NuGet source '{GITHUB_SOURCE_NAME}' is now working."))
            return True
        print(red("  NuGet source still not working after credential update."))
        print(yellow(f"  Verify your PAT has read:packages scope. See: {WIKI_URL}"))
        return False

    # Source does not exist — add it
    pat = resolve_pat(cli_token)
    if not pat:
        print(red("  No PAT provided. Cannot add NuGet source."))
        return False
    if not _add_nuget_source(pat):
        return False
    if _test_nuget_source():
        print(green(f"  NuGet source '{GITHUB_SOURCE_NAME}' configured and verified."))
        return True
    print(yellow("  NuGet source added but test search returned no results."))
    print(yellow(f"  Verify your PAT has read:packages scope. See: {WIKI_URL}"))
    return False


# ── NPM configuration ─────────────────────────────────────────────────────────


def _get_npm_registry() -> str | None:
    """Return the currently configured @moodysanalytics registry, or None."""
    result = run_cmd(["npm", "config", "get", f"@{GITHUB_ORG}:registry"])
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if value in ("undefined", ""):
        return None
    return value


def _npmrc_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".npmrc")


def _set_npm_auth_token(pat: str) -> None:
    """Ensure //npm.pkg.github.com/:_authToken=<PAT> is in ~/.npmrc."""
    npmrc = _npmrc_path()
    token_line = f"//npm.pkg.github.com/:_authToken={pat}"
    token_prefix = "//npm.pkg.github.com/:_authToken="

    lines: list[str] = []
    if os.path.isfile(npmrc):
        with open(npmrc, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.strip().startswith(token_prefix):
            new_lines.append(token_line + "\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(token_line + "\n")

    with open(npmrc, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(dim(f"  Updated {npmrc}"))


def configure_npm(cli_token: str | None) -> bool:
    """Configure NPM registry for GitHub Packages. Return True on success."""
    print()
    print(cyan("── NPM Registry Configuration ──"))
    print()

    if not shutil.which("npm"):
        print(dim("  npm not found on PATH. Skipping NPM configuration."))
        return True  # not a failure — npm is optional

    current = _get_npm_registry()
    if current and current.rstrip("/") == GITHUB_NPM_URL:
        print(green(f"  NPM registry for @{GITHUB_ORG} is already configured."))
        return True

    pat = resolve_pat(cli_token)
    if not pat:
        print(red("  No PAT provided. Cannot configure NPM registry."))
        return False

    print(dim(f"  Setting @{GITHUB_ORG}:registry -> {GITHUB_NPM_URL}"))
    result = run_cmd(["npm", "config", "set", f"@{GITHUB_ORG}:registry", GITHUB_NPM_URL])
    if result.returncode != 0:
        print(red(f"  Failed to set NPM registry: {result.stderr.strip()}"))
        return False

    _set_npm_auth_token(pat)
    print(green(f"  NPM registry for @{GITHUB_ORG} configured successfully."))
    return True


# ── Interactive menu ───────────────────────────────────────────────────────────


def show_menu() -> str | None:
    """Show interactive menu. Return 'nuget', 'npm', 'both', or None to exit."""
    print()
    print("  Select what to configure:")
    print()
    print(f"  {cyan('[1]')} Configure NuGet source")
    print(f"  {cyan('[2]')} Configure NPM registry")
    print(f"  {cyan('[3]')} Configure both")
    print(f"  {cyan('[X]')} Exit")
    print()

    while True:
        try:
            choice = input("  Enter your choice (1-3, or X to exit): ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if choice == "1":
            return "nuget"
        if choice == "2":
            return "npm"
        if choice == "3":
            return "both"
        if choice == "X":
            return None
        print(red("  Invalid input. Please enter 1, 2, 3, or X."))


# ── Show saved tokens ──────────────────────────────────────────────────────────


def _nuget_config_paths() -> list[str]:
    """Return candidate NuGet.Config paths for the current platform."""
    paths: list[str] = []
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            paths.append(os.path.join(appdata, "NuGet", "NuGet.Config"))
    paths.append(os.path.join(os.path.expanduser("~"), ".nuget", "NuGet", "NuGet.Config"))
    paths.append(os.path.join(os.path.expanduser("~"), ".config", "NuGet", "NuGet.Config"))
    return paths


def _read_nuget_token() -> str | None:
    """Read ClearTextPassword for the github source from NuGet.Config."""
    for config_path in _nuget_config_paths():
        if not os.path.isfile(config_path):
            continue
        try:
            tree = ET.parse(config_path)
        except ET.ParseError:
            continue
        root = tree.getroot()
        creds = root.find(f".//packageSourceCredentials/{GITHUB_SOURCE_NAME}")
        if creds is None:
            continue
        for add in creds.findall("add"):
            if add.get("key") == "ClearTextPassword":
                return add.get("value")
    return None


def _read_npmrc_token() -> str | None:
    """Read //npm.pkg.github.com/:_authToken from ~/.npmrc."""
    npmrc = _npmrc_path()
    prefix = "//npm.pkg.github.com/:_authToken="
    if not os.path.isfile(npmrc):
        return None
    try:
        with open(npmrc, encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith(prefix):
                    return stripped[len(prefix):]
    except OSError:
        pass
    return None


def _mask_token(token: str) -> str:
    """Show first 4 and last 4 chars, mask the rest."""
    if len(token) <= 12:
        return token[:4] + "*" * (len(token) - 4)
    return token[:4] + "*" * (len(token) - 8) + token[-4:]


def show_saved_tokens() -> None:
    """Print saved PATs from NuGet config and ~/.npmrc."""
    print()
    print(cyan("── Saved Tokens ──"))

    # NuGet
    print()
    nuget_token = _read_nuget_token()
    if nuget_token:
        print(f"  NuGet ({GITHUB_SOURCE_NAME}): {green(_mask_token(nuget_token))}")
        found_path = None
        for p in _nuget_config_paths():
            if os.path.isfile(p):
                try:
                    tree = ET.parse(p)
                    creds = tree.getroot().find(
                        f".//packageSourceCredentials/{GITHUB_SOURCE_NAME}"
                    )
                    if creds is not None:
                        found_path = p
                        break
                except ET.ParseError:
                    continue
        if found_path:
            print(dim(f"    from: {found_path}"))
    else:
        print(dim(f"  NuGet ({GITHUB_SOURCE_NAME}): not configured"))

    # NPM
    print()
    npm_token = _read_npmrc_token()
    if npm_token:
        print(f"  NPM  (@{GITHUB_ORG}):  {green(_mask_token(npm_token))}")
        print(dim(f"    from: {_npmrc_path()}"))
    else:
        print(dim(f"  NPM  (@{GITHUB_ORG}):  not configured"))

    # Check if they match
    if nuget_token and npm_token:
        if nuget_token == npm_token:
            print()
            print(dim("  Both tokens are the same PAT."))
        else:
            print()
            print(yellow("  Warning: NuGet and NPM are using different PATs."))

    print()


# ── Status check ──────────────────────────────────────────────────────────────


def check_status() -> None:
    """Print current NuGet and NPM configuration status."""
    print()
    print(cyan("── Configuration Status ──"))

    # NuGet
    print()
    if not shutil.which("dotnet"):
        print(red("  NuGet: dotnet CLI not found"))
    else:
        sources = _parse_nuget_sources()
        if GITHUB_SOURCE_NAME not in sources:
            print(red(f"  NuGet: source '{GITHUB_SOURCE_NAME}' not configured"))
        elif not sources[GITHUB_SOURCE_NAME]:
            print(yellow(f"  NuGet: source '{GITHUB_SOURCE_NAME}' exists but is disabled"))
        else:
            if _test_nuget_source():
                print(green(f"  NuGet: source '{GITHUB_SOURCE_NAME}' is configured and working"))
            else:
                print(yellow(f"  NuGet: source '{GITHUB_SOURCE_NAME}' exists but test search failed (PAT may be expired)"))

    # NPM
    print()
    if not shutil.which("npm"):
        print(dim("  NPM:   not installed (optional)"))
    else:
        registry = _get_npm_registry()
        if registry and registry.rstrip("/") == GITHUB_NPM_URL:
            print(green(f"  NPM:   @{GITHUB_ORG} registry is configured"))
        else:
            print(red(f"  NPM:   @{GITHUB_ORG} registry not configured"))

    # Tokens
    nuget_token = _read_nuget_token()
    npm_token = _read_npmrc_token()
    print()
    print(dim(f"  NuGet PAT: {'saved' if nuget_token else 'not found'}"))
    print(dim(f"  NPM   PAT: {'saved' if npm_token else 'not found'}"))
    print()


# ── Main ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure GitHub Package Registry for NuGet and/or NPM.",
    )
    parser.add_argument("--token", help="GitHub Personal Access Token (PAT)")

    parser.add_argument(
        "--check", action="store_true",
        help="Check current NuGet/NPM configuration status, then exit",
    )
    parser.add_argument(
        "--show-token", action="store_true",
        help="Show saved PATs from NuGet config and ~/.npmrc, then exit",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Configure both NuGet and NPM (skip menu)")
    group.add_argument("--nuget", action="store_true", help="Configure NuGet only (skip menu)")
    group.add_argument("--npm", action="store_true", help="Configure NPM only (skip menu)")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print()
    print(cyan("=== GitHub Package Registry Setup ==="))

    if args.check:
        check_status()
        return 0

    if args.show_token:
        show_saved_tokens()
        return 0

    # Always show current status first
    check_status()

    if args.all:
        scope = "both"
    elif args.nuget:
        scope = "nuget"
    elif args.npm:
        scope = "npm"
    else:
        scope = show_menu()
        if scope is None:
            print(yellow("  Exiting."))
            return 0

    ok = True

    if scope in ("nuget", "both"):
        if not configure_nuget(args.token):
            ok = False

    if scope in ("npm", "both"):
        if not configure_npm(args.token):
            ok = False

    print()
    if ok:
        print(green("Done."))
    else:
        print(red("One or more configurations failed. See messages above."))
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
