#!/usr/bin/env python3
"""
@title ZMAPI / ZMNET Package Updater
@description Interactive NuGet package updater for ZMAPI/ZMNET packages across all projects
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Cross-platform replacement for Update-Packages.ps1.

Workflow:
    1. Presents a menu listing each package individually, plus an "Update All" option.
    2. If a single package is selected, shows the 5 most recent versions to choose from.
    3. If "Update All" is selected, each package is updated to its latest version.
    4. Updates all packages.config files and .csproj HintPath / Version= references.
    5. Downloads the .nupkg and extracts it to the packages/ directory.
    6. Copies content files from the package's content/ directory to the web project.
    7. Ensures all copied content files are listed as <Content Include> in the .csproj.

Prerequisites:
    - dotnet CLI must be installed and on PATH (run dotnet-setup.py --install).
    - A NuGet source named "github" must be configured (run dotnet-registry.py --nuget).

Exit codes:
    0 - all updates succeeded (or nothing to do)
    1 - one or more updates failed

@example
Usage example:
    python dotnet-update-packages.py                              # interactive menu
    python dotnet-update-packages.py --all                        # update all to latest
    python dotnet-update-packages.py --package ZMAPI-Windows-X64.Resource
    python dotnet-update-packages.py --package ZMAPI-Windows-X64.Resource --version 4.91.2604.6124
    python dotnet-update-packages.py --dry-run                    # preview without changes

@requires dotnet CLI, NuGet source "github"
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# ── Constants ──────────────────────────────────────────────────────────────────

TARGET_PACKAGES = [
    "ZMAPI-Windows-X64.Resource",
    "ZMAPI-Windows-X64.SaaS",
]

GITHUB_SOURCE_NAME = "github"
WIKI_URL = "https://moodysanalytics.atlassian.net/wiki/spaces/CAO/pages/470036157/Connect+to+GitHub+Package+Registry"

CONTENT_INCLUDE_IGNORE_FILES: list[str] = [
    # Example: "resource\\SomeFile.dat"
]

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


# ── BOM-preserving file I/O ───────────────────────────────────────────────────
# CRITICAL: .csproj and packages.config files use UTF-8 with BOM in this repo.
# Writing without BOM will corrupt project files and break Visual Studio / MSBuild.

_UTF8_BOM = b"\xef\xbb\xbf"


class FileContent(NamedTuple):
    content: str
    has_bom: bool
    path: str


def read_file(path: str) -> FileContent:
    raw = Path(path).read_bytes()
    has_bom = raw[:3] == _UTF8_BOM
    content = raw.decode("utf-8-sig")
    return FileContent(content=content, has_bom=has_bom, path=path)


def write_file(fc: FileContent, content: str | None = None, *, dry_run: bool = False) -> None:
    text = content if content is not None else fc.content
    if dry_run:
        print(dim(f"  [dry-run] Would write {fc.path}"))
        return
    payload = (_UTF8_BOM if fc.has_bom else b"") + text.encode("utf-8")
    Path(fc.path).write_bytes(payload)


# ── File scan cache ────────────────────────────────────────────────────────────


class FileCache:
    """Scan packages.config and .csproj files once, reuse across updates."""

    def __init__(self, root: str) -> None:
        self.root = root
        self._packages_configs: list[str] | None = None
        self._csprojs: list[str] | None = None

    def packages_configs(self) -> list[str]:
        if self._packages_configs is None:
            self._packages_configs = [
                str(p) for p in Path(self.root).rglob("packages.config")
            ]
        return self._packages_configs

    def csprojs(self) -> list[str]:
        if self._csprojs is None:
            self._csprojs = [str(p) for p in Path(self.root).rglob("*.csproj")]
        return self._csprojs


# ── Prerequisites ──────────────────────────────────────────────────────────────


def check_prerequisites(source_name: str) -> bool:
    if not shutil.which("dotnet"):
        print(red("  ERROR: 'dotnet' CLI not found. Run: python3 dotnet-setup.py --install"))
        return False

    result = subprocess.run(
        ["dotnet", "nuget", "list", "source"],
        capture_output=True, text=True, timeout=15,
    )
    if source_name not in result.stdout:
        print(red(f"  ERROR: NuGet source '{source_name}' is not configured."))
        print(yellow("  Run: python3 dotnet-registry.py --nuget"))
        print(f"  See: {WIKI_URL}")
        return False

    return True


# ── Version query ──────────────────────────────────────────────────────────────


def _parse_version(v: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return None


def query_versions_dotnet(package_id: str, source_name: str) -> list[str]:
    """Query versions via `dotnet package search`. Returns sorted desc."""
    print(dim(f"  Querying '{package_id}' from source '{source_name}'..."))
    try:
        result = subprocess.run(
            ["dotnet", "package", "search", package_id,
             "--source", source_name, "--exact-match", "--format", "json"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return []

    versions: list[str] = []
    for source in data.get("searchResult", []):
        for pkg in source.get("packages", []):
            v = pkg.get("version")
            if v:
                versions.append(v)

    return _sort_versions(versions)


def _sort_versions(versions: list[str]) -> list[str]:
    parsed = [(v, _parse_version(v)) for v in versions]
    valid = [(v, t) for v, t in parsed if t is not None]
    valid.sort(key=lambda x: x[1], reverse=True)
    seen: set[tuple[int, ...]] = set()
    result: list[str] = []
    for v, t in valid:
        if t not in seen:
            seen.add(t)
            result.append(v)
    return result


def get_package_versions(package_id: str, source_name: str) -> list[str]:
    """Query versions via dotnet CLI."""
    versions = query_versions_dotnet(package_id, source_name)
    if not versions:
        print(yellow(f"  No versions found for '{package_id}'. Check access permissions."))
        print(dim(f"  See: {WIKI_URL}"))
    return versions


# ── Current version from packages.config ───────────────────────────────────────


def get_current_version(package_id: str, web_proj_dir: str) -> str | None:
    config_path = os.path.join(web_proj_dir, "packages.config")
    if not os.path.isfile(config_path):
        print(yellow(f"  WARNING: {config_path} not found."))
        return None
    content = Path(config_path).read_text(encoding="utf-8-sig")
    pattern = rf'<package\s+id="{re.escape(package_id)}"\s+version="([^"]+)"'
    m = re.search(pattern, content)
    return m.group(1) if m else None


# ── Update packages.config ────────────────────────────────────────────────────


def update_packages_configs(
    package_id: str, old_version: str, new_version: str,
    file_cache: FileCache, *, dry_run: bool = False,
) -> None:
    pattern = rf'(<package\s+id="{re.escape(package_id)}"\s+version=")([^"]+)(")'
    for cfg_path in file_cache.packages_configs():
        fc = read_file(cfg_path)
        if package_id not in fc.content:
            continue
        replaced = re.sub(pattern, rf"\g<1>{new_version}\3", fc.content)
        if replaced != fc.content:
            write_file(fc, replaced, dry_run=dry_run)
            print(dim(f"  Updated {cfg_path}"))


# ── Update .csproj HintPath + Version= references ────────────────────────────


def update_csproj_references(
    package_id: str, old_version: str, new_version: str,
    file_cache: FileCache, *, dry_run: bool = False,
) -> None:
    old_fragment = f"{package_id}.{old_version}"
    new_fragment = f"{package_id}.{new_version}"

    for proj_path in file_cache.csprojs():
        fc = read_file(proj_path)
        if old_fragment not in fc.content:
            continue
        replaced = fc.content.replace(old_fragment, new_fragment)
        if replaced != fc.content:
            write_file(fc, replaced, dry_run=dry_run)
            print(dim(f"  Updated references in {proj_path}"))



# ── Download package via dotnet restore ─────────────────────────────────────────


def download_package(
    package_id: str, version: str, packages_dir: str,
    *, dry_run: bool = False,
) -> bool:
    """Download package via `dotnet restore` and place it in packages_dir. Return True on success."""
    target_dir = os.path.join(packages_dir, f"{package_id}.{version}")
    if os.path.isdir(target_dir):
        print(dim(f"  Package already present: {target_dir}"))
        return True

    if dry_run:
        print(dim(f"  [dry-run] Would download '{package_id}' v{version}"))
        return True

    print(cyan(f"  Downloading '{package_id}' v{version} via dotnet restore..."))

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Minimal .csproj to trigger package download only.
        # Use netstandard2.0 to avoid downloading .NET Framework targeting packs.
        csproj_content = (
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            '  <PropertyGroup>\n'
            '    <TargetFramework>netstandard2.0</TargetFramework>\n'
            '    <AutoGenerateBindingRedirects>false</AutoGenerateBindingRedirects>\n'
            '  </PropertyGroup>\n'
            '  <ItemGroup>\n'
            f'    <PackageReference Include="{package_id}" Version="{version}" />\n'
            '  </ItemGroup>\n'
            '</Project>\n'
        )
        tmp_csproj = os.path.join(tmp_dir, "tmp_restore.csproj")
        Path(tmp_csproj).write_text(csproj_content)

        tmp_packages = os.path.join(tmp_dir, "pkgs")
        log_file = os.path.join(tmp_dir, "restore.log")
        with open(log_file, "w") as log_f:
            result = subprocess.run(
                ["dotnet", "restore", tmp_csproj, "--packages", tmp_packages],
                stdout=log_f, stderr=subprocess.STDOUT, text=True, timeout=180,
            )

        if result.returncode != 0:
            print(red("  dotnet restore failed:"))
            try:
                log_content = Path(log_file).read_text()
                for line in log_content.splitlines():
                    if "error" in line.lower():
                        print(red(f"    {line.strip()}"))
            except OSError:
                pass
            print(yellow(f"  Check your PAT and source config. See: {WIKI_URL}"))
            return False

        # dotnet restore puts packages at {tmp_packages}/{lowercase_id}/{version}/
        restored_dir = os.path.join(tmp_packages, package_id.lower(), version)
        if not os.path.isdir(restored_dir):
            print(red(f"  Package not found in restore output: {restored_dir}"))
            return False

        os.makedirs(packages_dir, exist_ok=True)
        shutil.copytree(restored_dir, target_dir)

    if not os.path.isdir(target_dir):
        print(red(f"  Package directory not created: {target_dir}"))
        return False

    print(green(f"  Downloaded to {target_dir}"))
    return True


# ── Copy content files to web project ──────────────────────────────────────────


def copy_package_content(
    package_id: str, version: str, packages_dir: str, web_proj_dir: str,
    *, dry_run: bool = False,
) -> list[str]:
    """Copy content/ files from package to web project. Return list of relative paths."""
    content_dir = os.path.join(packages_dir, f"{package_id}.{version}", "content")
    if not os.path.isdir(content_dir):
        return []

    content_path = Path(content_dir)
    files = [f for f in content_path.rglob("*") if f.is_file()]
    if not files:
        return []

    copied: list[str] = []
    print(dim(f"  Copying content to {os.path.basename(web_proj_dir)}..."))
    for f in files:
        rel_path = str(f.relative_to(content_path))
        dest = os.path.join(web_proj_dir, rel_path)

        if dry_run:
            print(dim(f"  [dry-run] Would copy {rel_path}"))
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(str(f), dest)

        copied.append(rel_path)

    action = "Would copy" if dry_run else "Copied"
    print(dim(f"  {action} {len(copied)} content file(s)."))
    return copied


# ── Update <Content Include> in .csproj ────────────────────────────────────────


def update_csproj_content_includes(
    content_rel_paths: list[str], web_proj_dir: str,
    *, dry_run: bool = False,
) -> None:
    if not content_rel_paths:
        return

    csproj_files = list(Path(web_proj_dir).glob("*.csproj"))
    for csproj_path in csproj_files:
        fc = read_file(str(csproj_path))
        modified = False

        for rel_path in content_rel_paths:
            if rel_path.lower() in (ig.lower() for ig in CONTENT_INCLUDE_IGNORE_FILES):
                continue

            # csproj may use \ or / as separator — match either
            pat = re.escape(rel_path).replace("/", r"[/\\]")
            if re.search(rf'(?i)<Content\s+Include="{pat}"', fc.content):
                continue

            new_entry = f'    <Content Include="{rel_path}" />'
            last_close = fc.content.rfind("</ItemGroup>")
            if last_close != -1:
                fc = fc._replace(
                    content=fc.content[:last_close] + new_entry + "\r\n  " + fc.content[last_close:]
                )
                modified = True
                print(cyan(f"  Added <Content Include=\"{rel_path}\"> to {csproj_path.name}"))

        if modified:
            write_file(fc, dry_run=dry_run)


# ── Single package update orchestration ────────────────────────────────────────


class UpdateResult(NamedTuple):
    package_id: str
    old_version: str | None
    new_version: str
    status: str  # "updated", "skipped", "failed"


def update_single_package(
    package_id: str, new_version: str,
    root: str, web_proj_dir: str, packages_dir: str,
    file_cache: FileCache,
    *, dry_run: bool = False,
) -> UpdateResult:
    current = get_current_version(package_id, web_proj_dir)
    if not current:
        print(yellow(f"  '{package_id}' not found in packages.config. Skipping."))
        return UpdateResult(package_id, None, new_version, "skipped")

    if current == new_version:
        print(yellow(f"  '{package_id}' is already at version {new_version}. Skipping."))
        return UpdateResult(package_id, current, new_version, "skipped")

    print(green(f"  Updating '{package_id}': {current} -> {new_version}"))

    # Download FIRST — only modify project files after a successful download
    ok = download_package(package_id, new_version, packages_dir, dry_run=dry_run)
    if not ok:
        print(red(f"  Download failed. No files were modified for '{package_id}'."))
        return UpdateResult(package_id, current, new_version, "failed")

    update_packages_configs(package_id, current, new_version, file_cache, dry_run=dry_run)
    update_csproj_references(package_id, current, new_version, file_cache, dry_run=dry_run)

    copied = copy_package_content(
        package_id, new_version, packages_dir, web_proj_dir, dry_run=dry_run,
    )
    update_csproj_content_includes(copied, web_proj_dir, dry_run=dry_run)

    return UpdateResult(package_id, current, new_version, "updated")


# ── Interactive menus ──────────────────────────────────────────────────────────


def show_package_menu(current_versions: dict[str, str | None]) -> str | None:
    """Show package selection menu. Return package name, 'ALL', or None to exit."""
    print()
    print(yellow("Select a package to update:"))
    print()
    print(f"  {green('[0]')} Update ALL packages to latest version")
    for i, pkg in enumerate(TARGET_PACKAGES):
        cur = current_versions.get(pkg)
        if cur:
            print(f"  {cyan(f'[{i + 1}]')} {pkg}  (current: {cur})")
        else:
            print(f"  {dim(f'[{i + 1}]')} {pkg}  {dim('(not installed)')}")

    pkg_max = len(TARGET_PACKAGES)
    print()

    while True:
        try:
            raw = input(f"  Enter your choice (0-{pkg_max}, or X to exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw.upper() == "X":
            return None
        try:
            num = int(raw)
        except ValueError:
            print(red(f"  Invalid input. Enter 0-{pkg_max}, or X."))
            continue
        if num == 0:
            return "ALL"
        if 1 <= num <= pkg_max:
            return TARGET_PACKAGES[num - 1]
        print(red(f"  Invalid input. Enter 0-{pkg_max}, or X."))


def show_version_menu(versions: list[str]) -> str | None:
    """Show version selection menu. Return selected version or None to exit."""
    show_count = min(5, len(versions))
    total = len(versions)
    displayed = show_count  # how many are currently listed

    def _print_list(count: int) -> None:
        print()
        header = "All versions:" if count == total else f"Available versions (latest {count}):"
        print(yellow(header))
        for i in range(count):
            label = " (latest)" if i == 0 else ""
            print(f"  {cyan(f'[{i + 1}]')} {versions[i]}{label}")
        print()

    _print_list(displayed)

    while True:
        try:
            raw = input(f"  Select version (1-{displayed}, version number, or X to exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw.upper() == "X":
            return None
        # Direct version number input (e.g. "4.91.2604.6124")
        if "." in raw and any(c.isdigit() for c in raw):
            if raw in versions:
                return raw
            # Show full list so user can pick
            print(red(f"  Version '{raw}' not found."))
            if displayed < total:
                displayed = total
                _print_list(displayed)
            continue
        try:
            num = int(raw)
        except ValueError:
            print(red(f"  Invalid input. Enter 1-{displayed}, a version number, or X."))
            continue
        if 1 <= num <= displayed:
            return versions[num - 1]
        print(red(f"  Invalid input. Enter 1-{displayed}, a version number, or X."))


# ── Summary ────────────────────────────────────────────────────────────────────


def print_summary(results: list[UpdateResult]) -> None:
    if not results:
        return

    print()
    print(cyan("── Summary ──"))
    print()

    status_map = {
        "updated": green("updated"),
        "skipped": yellow("skipped"),
        "failed": red("FAILED"),
    }

    # Build plain-text rows for width calculation, and display rows with color
    plain_rows: list[list[str]] = []
    color_rows: list[list[str]] = []
    for r in results:
        old = r.old_version or "n/a"
        arrow = "->" if r.status != "skipped" else ""
        new = r.new_version if r.status != "skipped" else ""
        status_plain = r.status.upper() if r.status == "failed" else r.status
        plain_rows.append([r.package_id, old, arrow, new, status_plain])
        color_rows.append([r.package_id, old, arrow, new, status_map.get(r.status, r.status)])

    # Compute widths from plain text, then apply to color rows
    col_count = len(plain_rows[0])
    widths = [0] * col_count
    for row in plain_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    for plain, color in zip(plain_rows, color_rows):
        parts = []
        for i, cell in enumerate(color):
            if i == col_count - 1:
                parts.append(cell)
            else:
                pad = widths[i] - len(plain[i])
                parts.append(cell + " " * pad)
        print("  " + "  ".join(parts))

    print()


# ── CLI ────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update ZMAPI/ZMNET NuGet packages across all projects.",
    )
    parser.add_argument(
        "--web-proj", default="ZMnetAdmin",
        help="Primary project directory (default: ZMnetAdmin)",
    )
    parser.add_argument(
        "--packages-dir", default="packages",
        help="Solution-level packages directory (default: packages)",
    )
    parser.add_argument(
        "--source", default=GITHUB_SOURCE_NAME,
        help=f"NuGet source name (default: {GITHUB_SOURCE_NAME})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without modifying any files",
    )
    parser.add_argument(
        "--package",
        help="Update a specific package (skip menu)",
    )
    parser.add_argument(
        "--version",
        help="Target version (use with --package, skip version menu)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Update all packages to latest version",
    )
    return parser.parse_args()


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> int:
    args = parse_args()

    print()
    print(cyan("=== ZMAPI / ZMNET Package Updater ==="))
    print("Updates packages.config, .csproj references, and content files across all projects.")
    print()

    if args.dry_run:
        print(yellow("  *** DRY-RUN MODE — no files will be modified ***"))
        print()

    # Resolve root directory (script location or cwd)
    root = os.path.dirname(os.path.abspath(__file__)) or os.getcwd()
    web_proj_dir = os.path.join(root, args.web_proj)
    packages_dir = os.path.join(root, args.packages_dir)

    if not check_prerequisites(args.source):
        return 1

    file_cache = FileCache(root)

    # Build current-version table
    current_versions: dict[str, str | None] = {}
    for pkg in TARGET_PACKAGES:
        current_versions[pkg] = get_current_version(pkg, web_proj_dir)

    results: list[UpdateResult] = []

    if args.all:
        # Update all packages to latest
        print(cyan("Fetching latest versions..."))
        for pkg in TARGET_PACKAGES:
            versions = get_package_versions(pkg, args.source)
            if not versions:
                results.append(UpdateResult(pkg, current_versions.get(pkg), "?", "failed"))
                continue
            r = update_single_package(
                pkg, versions[0], root, web_proj_dir, packages_dir,
                file_cache, dry_run=args.dry_run,
            )
            results.append(r)

    elif args.package:
        # Update a specific package
        if args.package not in TARGET_PACKAGES:
            print(red(f"  Unknown package: {args.package}"))
            print(f"  Valid packages: {', '.join(TARGET_PACKAGES)}")
            return 1

        if args.version:
            target_version = args.version
        else:
            versions = get_package_versions(args.package, args.source)
            if not versions:
                return 1
            target_version = show_version_menu(versions)
            if not target_version:
                print(yellow("  Exiting."))
                return 0

        r = update_single_package(
            args.package, target_version, root, web_proj_dir, packages_dir,
            file_cache, dry_run=args.dry_run,
        )
        results.append(r)

    else:
        # Interactive menu
        choice = show_package_menu(current_versions)
        if choice is None:
            print(yellow("  Exiting."))
            return 0

        if choice == "ALL":
            print()
            print(cyan("Fetching latest versions..."))
            for pkg in TARGET_PACKAGES:
                versions = get_package_versions(pkg, args.source)
                if not versions:
                    results.append(UpdateResult(pkg, current_versions.get(pkg), "?", "failed"))
                    continue
                r = update_single_package(
                    pkg, versions[0], root, web_proj_dir, packages_dir,
                    file_cache, dry_run=args.dry_run,
                )
                results.append(r)
        else:
            print()
            print(cyan(f"Fetching versions for '{choice}'..."))
            versions = get_package_versions(choice, args.source)
            if not versions:
                return 1
            target_version = show_version_menu(versions)
            if not target_version:
                print(yellow("  Exiting."))
                return 0
            print()
            r = update_single_package(
                choice, target_version, root, web_proj_dir, packages_dir,
                file_cache, dry_run=args.dry_run,
            )
            results.append(r)

    print_summary(results)

    any_failed = any(r.status == "failed" for r in results)
    any_updated = any(r.status == "updated" for r in results)

    if any_failed:
        print(red("Some updates failed. See messages above."))
    elif any_updated:
        print(green("Done. Please rebuild the solution to verify the update."))
    else:
        print(yellow("Nothing to update."))
    print()

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
