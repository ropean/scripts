#!/usr/bin/env python3
"""
@title path-utils
@description Cross-platform path resolver: Windows, macOS, Linux, WSL.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Parses and resolves file paths from any of the following formats:
  - Windows absolute:   C:\\Users\\foo\\file.env   or   C:/Users/foo/file.env
  - UNC:                \\\\server\\share\\file.env
  - WSL mount:          /mnt/c/Users/foo/file.env
  - Unix absolute:      /home/foo/file.env
  - Tilde-expanded:     ~/projects/file.env
  - Relative:           ../file.env  or  .dev.vars

Can be used as a module (import resolve_path) or run directly for testing.

@example
    # As a module:
    from path_utils import resolve_path
    p = resolve_path("C:/Users/foo/.dev.vars")

    # Self-test:
    python path-utils.py --test

@requires pathlib, platform
@see md-files/help/script-template.md
"""

import os
import platform
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

# ════════════════════════════════════════════════════════════
#  PLATFORM DETECTION
# ════════════════════════════════════════════════════════════

def _running_platform() -> str:
    """Return 'windows', 'wsl', 'macos', or 'linux'."""
    if sys.platform == "win32":
        return "windows"
    uname = platform.uname()
    if "microsoft" in uname.release.lower() or "microsoft" in uname.version.lower():
        return "wsl"
    if sys.platform == "darwin":
        return "macos"
    return "linux"

CURRENT_PLATFORM = _running_platform()

# ════════════════════════════════════════════════════════════
#  PATH CLASSIFIER
# ════════════════════════════════════════════════════════════

_WIN_ABS   = re.compile(r'^[A-Za-z]:[/\\]')   # C:\ or C:/
_UNC       = re.compile(r'^[/\\]{2}[^/\\]')    # \\server or //server
_WSL_MOUNT = re.compile(r'^/mnt/[a-z]/')       # /mnt/c/...

def _classify(path_str: str) -> str:
    s = path_str.strip()
    if _WIN_ABS.match(s):
        return "windows_abs"
    if _UNC.match(s):
        return "unc"
    if _WSL_MOUNT.match(s):
        return "wsl_mount"
    if s.startswith("~"):
        return "tilde"
    if s.startswith("/") or s.startswith("./") or s.startswith("../"):
        return "unix"
    # bare relative (no leading slash or dot-slash)
    return "relative"


# ════════════════════════════════════════════════════════════
#  CONVERSION HELPERS
# ════════════════════════════════════════════════════════════

def _win_abs_to_path(s: str) -> Path:
    """C:/Users/foo or C:\\Users\\foo → Path on any OS."""
    if CURRENT_PLATFORM in ("windows",):
        return Path(s)
    # On WSL/Linux/macOS, convert to /mnt/c/... style
    drive = s[0].lower()
    rest  = s[2:].replace("\\", "/").lstrip("/")
    return Path(f"/mnt/{drive}/{rest}")


def _unc_to_path(s: str) -> Path:
    """\\\\server\\share\\path → Path (Windows only; warn elsewhere)."""
    if CURRENT_PLATFORM == "windows":
        return Path(s)
    # UNC not natively supported on Linux/macOS — return as-is and let the
    # caller handle the resulting error
    return Path(s.replace("\\", "/"))


def _wsl_mount_to_path(s: str) -> Path:
    """
    /mnt/c/Users/foo  →  C:\\Users\\foo on Windows,
                      →  /mnt/c/Users/foo on WSL/Linux (already valid).
    """
    if CURRENT_PLATFORM == "windows":
        # /mnt/c/Users/foo → C:\Users\foo
        parts = PurePosixPath(s).parts  # ('/', 'mnt', 'c', 'Users', 'foo')
        drive  = parts[2].upper() + ":\\"
        rest   = "\\".join(parts[3:])
        return Path(drive + rest)
    return Path(s)


# ════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════

def resolve_path(path_str: str) -> Path:
    """
    Parse *path_str* into a fully-resolved, absolute :class:`pathlib.Path`
    on the current OS.

    Supports:
      - Windows absolute  (C:/…  or  C:\\…)
      - UNC               (\\\\server\\share\\…)
      - WSL mount         (/mnt/c/…)
      - Tilde             (~/…)
      - Unix absolute     (/home/…)
      - Relative          (./…  ../…  or  bare name)

    Returns the Path object; does **not** assert existence so you can use it
    for output paths too.
    """
    s = path_str.strip()
    kind = _classify(s)

    if kind == "windows_abs":
        p = _win_abs_to_path(s)
    elif kind == "unc":
        p = _unc_to_path(s)
    elif kind == "wsl_mount":
        p = _wsl_mount_to_path(s)
    elif kind == "tilde":
        p = Path(s).expanduser()
    else:  # unix absolute or relative
        p = Path(s)

    return p.resolve()


# ════════════════════════════════════════════════════════════
#  SELF-TEST
# ════════════════════════════════════════════════════════════

_TEST_CASES = [
    # (label, path_str, expected_fragment_on_platform)
    # expected_fragment is a substring we look for in the resolved string
    ("Windows abs (forward slash)",  "C:/Users/test/.env",         None),
    ("Windows abs (backslash)",      r"C:\Users\test\.env",        None),
    ("WSL mount path",               "/mnt/c/Users/test/.env",     None),
    ("Tilde expansion",              "~/.env",                     None),
    ("Unix absolute",                "/tmp/test/.env",             None),
    ("Relative dot-slash",           "./.env",                     None),
    ("Relative bare",                ".env",                       None),
]


def _color(code: int, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def run_tests() -> None:
    print(f"\nPlatform detected: {_color(36, CURRENT_PLATFORM)}\n")
    pad = max(len(lbl) for lbl, _, _ in _TEST_CASES) + 2
    passes = 0

    for label, raw, _ in _TEST_CASES:
        try:
            result = resolve_path(raw)
            status = _color(32, "PASS")
            detail = str(result)
            passes += 1
        except Exception as exc:
            status = _color(31, "FAIL")
            detail = f"ERROR: {exc}"

        print(f"  {status}  {label:<{pad}}  {_color(33, repr(raw))}")
        print(f"         -> {detail}\n")

    total = len(_TEST_CASES)
    summary = _color(32 if passes == total else 31, f"{passes}/{total} passed")
    print(f"Results: {summary}\n")


# ════════════════════════════════════════════════════════════
#  CLI ENTRY
# ════════════════════════════════════════════════════════════

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Cross-platform path resolver utility.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run --test to execute the built-in test suite.",
    )
    parser.add_argument("path", nargs="?", help="Path string to resolve")
    parser.add_argument("--test", action="store_true", help="Run self-test suite")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    if args.path:
        result = resolve_path(args.path)
        print(result)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
