#!/usr/bin/env python3
"""
@title dotfile
@description Copy config files into the dotfiles/ directory, organized by project.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Supports glob patterns and unquoted paths with spaces.

@example
    python scripts/dotfile.py <path> [<path> ...]
    python scripts/dotfile.py D:\\Git\\project\\env\\.env
    python scripts/dotfile.py D:\\Git\\project\\config\\*.json
    python scripts/dotfile.py C:\\Program Files\\App\\config.xml
"""

import sys
import shutil
from glob import glob
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
DOTFILES_DIR = SCRIPTS_DIR.parent / "dotfiles"
COMMON_CONFIG_DIRS = {"env", "config", "configs", ".config", "environments", "settings"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def target_path(src: Path) -> Path:
    parent = src.parent
    if parent.name.lower() in COMMON_CONFIG_DIRS:
        project = parent.parent.name
    else:
        project = parent.name
    return DOTFILES_DIR / project / src.name


def copy_file(src: Path) -> bool:
    if not src.exists():
        print(f"  ✗  not found: {src}", file=sys.stderr)
        return False
    if not src.is_file():
        print(f"  ✗  not a file: {src}", file=sys.stderr)
        return False
    dst = target_path(src)
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  ✓  {src}")
        print(f"     → {dst}")
        return True
    except OSError as e:
        print(f"  ✗  {src}: {e}", file=sys.stderr)
        return False


def expand_args(args: list[str]) -> list[Path]:
    """
    Expand glob patterns; merge consecutive tokens that form a path with spaces.
    """
    files: list[Path] = []
    i = 0
    while i < len(args):
        # Try progressively longer merges to handle unquoted paths with spaces
        merged = args[i]
        j = i + 1
        while j < len(args):
            candidate = merged + " " + args[j]
            if Path(candidate).exists() or any(c in candidate for c in ("*", "?")):
                merged = candidate
                j += 1
                if Path(merged).exists():
                    break
            else:
                break

        matches = glob(merged, recursive=True)
        if matches:
            files.extend(Path(m) for m in matches if Path(m).is_file())
        else:
            files.append(Path(merged))  # let copy_file report missing

        i = j if j > i + 1 else i + 1

    return files


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: python scripts/dotfile.py <path> [<path> ...]")
        print("       Supports glob patterns and unquoted paths with spaces.")
        sys.exit(1)

    print(f"Dotfiles directory: {DOTFILES_DIR}\n")

    files = expand_args(args)
    ok = sum(copy_file(f) for f in files)
    print(f"\n[done] {ok}/{len(files)} copied")


if __name__ == "__main__":
    main()
