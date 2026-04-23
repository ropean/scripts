#!/usr/bin/env python3
"""
@title .NET SDK Setup Check
@description Verify the .NET SDK is installed and optionally auto-install it
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Verify that the .NET SDK is installed and accessible on PATH.
If `dotnet` is not found or the version check fails, prints actionable
installation instructions for every major platform and exits with code 1.
With --install, automatically downloads and installs the recommended SDK
version and configures the shell PATH.

Exit codes:
    0 - dotnet CLI is available
    1 - dotnet CLI is missing or broken

@example
Usage example:
    python dotnet-setup.py              # check only
    python dotnet-setup.py --install    # auto-install if missing
"""

import argparse
import os
import shutil
import subprocess
import sys

# ── Constants ──────────────────────────────────────────────────────────────────

RECOMMENDED_MAJOR = "8"

DOWNLOAD_URL = f"https://dotnet.microsoft.com/en-us/download/dotnet/{RECOMMENDED_MAJOR}.0"
PS_INSTALL_SCRIPT = "https://builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.ps1"
BASH_INSTALL_SCRIPT = "https://builds.dotnet.microsoft.com/dotnet/scripts/v1/dotnet-install.sh"

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


# ── Core logic ─────────────────────────────────────────────────────────────────


def check_dotnet() -> bool:
    """Return True if `dotnet --version` succeeds."""
    if not shutil.which("dotnet"):
        return False
    try:
        result = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except (OSError, subprocess.TimeoutExpired):
        return False


def get_dotnet_version() -> str:
    result = subprocess.run(
        ["dotnet", "--version"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip()


def print_install_instructions() -> None:
    is_windows = sys.platform == "win32"
    is_mac = sys.platform == "darwin"

    print()
    print(red("ERROR: 'dotnet' CLI is not installed or not on PATH."))
    print()
    print(f"  .NET {RECOMMENDED_MAJOR} (recommended) is required. Install using one of these methods:")
    print()

    idx = 1
    print(f"  {cyan(f'{idx}.')} Download installer:")
    print(f"     {DOWNLOAD_URL}")
    print()
    idx += 1

    if is_windows:
        print(f"  {cyan(f'{idx}.')} PowerShell:")
        print(f"     Invoke-WebRequest '{PS_INSTALL_SCRIPT}' -OutFile dotnet-install.ps1")
        print(f"     ./dotnet-install.ps1 -Channel {RECOMMENDED_MAJOR}.0")
        print()
        idx += 1

    print(f"  {cyan(f'{idx}.')} Bash:")
    print(f"     curl -fsSL {BASH_INSTALL_SCRIPT} | bash /dev/stdin --channel {RECOMMENDED_MAJOR}.0")
    print()
    idx += 1

    if is_mac:
        print(f"  {cyan(f'{idx}.')} Homebrew:")
        print(f"     brew install dotnet@{RECOMMENDED_MAJOR}")
        print()

    print(dim("  After installation, restart your terminal and re-run this script."))
    print()


# ── Auto-install ───────────────────────────────────────────────────────────────

DOTNET_INSTALL_DIR = os.path.join(os.path.expanduser("~"), ".dotnet")


def _shell_profile_path() -> str | None:
    """Return the most appropriate shell profile for the current user."""
    home = os.path.expanduser("~")
    shell = os.environ.get("SHELL", "")

    if "zsh" in shell:
        candidates = [".zshrc", ".zprofile"]
    elif "bash" in shell:
        candidates = [".bashrc", ".bash_profile", ".profile"]
    else:
        candidates = [".profile"]

    for name in candidates:
        path = os.path.join(home, name)
        if os.path.isfile(path):
            return path

    # Fallback: create the first candidate
    return os.path.join(home, candidates[0])


def _path_already_configured(profile_path: str) -> bool:
    """Check if .dotnet is already exported in the shell profile."""
    if not os.path.isfile(profile_path):
        return False
    try:
        with open(profile_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        return ".dotnet" in content and "PATH" in content
    except OSError:
        return False


def _add_path_to_profile(profile_path: str) -> bool:
    """Append dotnet PATH export to the shell profile. Return True on success."""
    export_block = (
        '\n# .NET SDK\n'
        f'export DOTNET_ROOT="{DOTNET_INSTALL_DIR}"\n'
        f'export PATH="$DOTNET_ROOT:$PATH"\n'
    )
    try:
        with open(profile_path, "a", encoding="utf-8") as f:
            f.write(export_block)
        return True
    except OSError as e:
        print(red(f"  Failed to update {profile_path}: {e}"))
        return False


def install_dotnet() -> int:
    """Download and install .NET SDK, then configure PATH."""
    is_windows = sys.platform == "win32"

    print()
    print(cyan(f"  Installing .NET {RECOMMENDED_MAJOR}.0 SDK..."))
    print()

    if is_windows:
        # Download and run PowerShell install script
        ps_local = os.path.join(os.environ.get("TEMP", "."), "dotnet-install.ps1")
        print(dim(f"  Downloading install script to {ps_local}..."))
        dl = subprocess.run(
            ["powershell", "-Command",
             f"Invoke-WebRequest '{PS_INSTALL_SCRIPT}' -OutFile '{ps_local}' -UseBasicParsing"],
            capture_output=True, text=True, timeout=60,
        )
        if dl.returncode != 0:
            print(red(f"  Failed to download install script: {dl.stderr.strip()}"))
            return 1

        print(dim(f"  Running install script (channel {RECOMMENDED_MAJOR}.0)..."))
        install = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_local,
             "-Channel", f"{RECOMMENDED_MAJOR}.0"],
            timeout=300,
        )
    else:
        # Download and run Bash install script
        print(dim(f"  Downloading and running install script (channel {RECOMMENDED_MAJOR}.0)..."))
        curl = subprocess.run(
            ["curl", "-fsSL", BASH_INSTALL_SCRIPT],
            capture_output=True, timeout=60,
        )
        if curl.returncode != 0:
            print(red("  Failed to download install script."))
            return 1

        install = subprocess.run(
            ["bash", "/dev/stdin", "--channel", f"{RECOMMENDED_MAJOR}.0"],
            input=curl.stdout, timeout=300,
        )

    if install.returncode != 0:
        print(red("  Installation failed. See output above."))
        return 1

    # Verify the binary exists
    dotnet_bin = os.path.join(DOTNET_INSTALL_DIR, "dotnet")
    if is_windows:
        dotnet_bin += ".exe"
    if not os.path.isfile(dotnet_bin):
        print(red(f"  Expected binary not found: {dotnet_bin}"))
        return 1

    # Get installed version
    ver_result = subprocess.run(
        [dotnet_bin, "--version"], capture_output=True, text=True, timeout=15,
    )
    version = ver_result.stdout.strip() if ver_result.returncode == 0 else "unknown"
    print(green(f"  Installed .NET SDK v{version} to {DOTNET_INSTALL_DIR}"))

    # Configure PATH
    if is_windows:
        print()
        print(yellow("  To add dotnet to your PATH permanently on Windows, run:"))
        print(f'     [Environment]::SetEnvironmentVariable("PATH", "{DOTNET_INSTALL_DIR};$env:PATH", "User")')
        print()
    else:
        profile = _shell_profile_path()
        if profile and not _path_already_configured(profile):
            if _add_path_to_profile(profile):
                print(green(f"  Added dotnet to PATH in {profile}"))
                print(dim("  Run the following to apply now, or restart your terminal:"))
                print(dim(f"    source {profile}"))
            else:
                print(yellow(f"  Could not update {profile}. Add manually:"))
                print(f'     export PATH="{DOTNET_INSTALL_DIR}:$PATH"')
        elif profile:
            print(dim(f"  PATH already configured in {profile}"))
        else:
            print(yellow("  Add this to your shell profile:"))
            print(f'     export PATH="{DOTNET_INSTALL_DIR}:$PATH"')

    print()
    return 0


# ── Main ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check (and optionally install) the .NET SDK.",
    )
    parser.add_argument(
        "--install", action="store_true",
        help=f"Auto-install .NET {RECOMMENDED_MAJOR} SDK and configure PATH",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print()
    print(cyan("=== .NET SDK Setup Check ==="))
    print()

    if check_dotnet():
        version = get_dotnet_version()
        print(green(f"  dotnet CLI is available: v{version}"))

        major = version.split(".")[0]
        if major != RECOMMENDED_MAJOR:
            print(yellow(f"  Note: Recommended version is .NET {RECOMMENDED_MAJOR}.x, you have {version}."))
            print(yellow(f"  This may still work, but consider upgrading: {DOWNLOAD_URL}"))

        print()
        return 0

    if args.install:
        return install_dotnet()

    print_install_instructions()
    print(dim(f"  Or run this script with --install to auto-install .NET {RECOMMENDED_MAJOR}:"))
    print(dim(f"    python3 {os.path.basename(__file__)} --install"))
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
