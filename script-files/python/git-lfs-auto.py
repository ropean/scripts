#!/usr/bin/env python3
"""
@title git-lfs-auto
@description Scan a directory for large files and register them with Git LFS.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

For every file exceeding SIZE_THRESHOLD_MB the script:
  1. Ensures git is initialised in the directory (or its repo root).
  2. Ensures `git lfs install` has been run.
  3. Runs `git lfs track` for each new large-file extension pattern
     (or exact filename when the file has no extension).
  4. Stages the resulting .gitattributes change.

Supports Windows absolute paths, relative paths, and WSL UNC paths
(\\\\wsl.localhost\\<distro>\\... or \\\\wsl$\\<distro>\\...).

@example
    python git-lfs-auto.py "D:\\Projects\\my-repo"
    python git-lfs-auto.py "D:\\Projects\\my-repo" --dry-run
    python git-lfs-auto.py "D:\\Projects\\my-repo" --threshold 10
    python git-lfs-auto.py "\\\\wsl.localhost\\Ubuntu\\home\\user\\repo"
    python git-lfs-auto.py .
"""

from __future__ import annotations

# ════════════════════════════════════════════════════════════
#  USER CONFIG
# ════════════════════════════════════════════════════════════

SIZE_THRESHOLD_MB: float = 4.0   # Files larger than this are tracked by LFS

_SKIP_DIRS: set[str] = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# ════════════════════════════════════════════════════════════
#  END OF USER CONFIG
# ════════════════════════════════════════════════════════════

import argparse
import os
import subprocess
import sys
from pathlib import Path


# ── Terminal colors ───────────────────────────────────────

def _supports_color() -> bool:
    term = os.environ.get("TERM", "")
    if os.environ.get("FORCE_COLOR") or os.environ.get("COLORTERM"):
        return True
    if term and term != "dumb":
        return True
    if os.name == "nt" and (os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM")):
        return True
    return sys.stdout.isatty()


if _supports_color():
    _C = {
        "red":    "\033[31m",
        "yellow": "\033[33m",
        "green":  "\033[32m",
        "cyan":   "\033[36m",
        "bold":   "\033[1m",
        "dim":    "\033[2m",
        "reset":  "\033[0m",
    }
else:
    _C = {k: "" for k in ("red", "yellow", "green", "cyan", "bold", "dim", "reset")}


def c(color: str, text: str) -> str:
    return f"{_C[color]}{text}{_C['reset']}"


# ── Path helpers ──────────────────────────────────────────

def _wsl_path(p: Path) -> tuple[str, str] | None:
    """If p is a WSL UNC path, return (distro, linux_path); else None."""
    s = str(p)
    for prefix in ("\\\\wsl.localhost\\", "\\\\wsl$\\"):
        if s.startswith(prefix):
            rest = s[len(prefix):]          # "Ubuntu\home\user\repo"
            parts = rest.split("\\", 1)
            distro = parts[0]
            linux_path = ("/" + parts[1].replace("\\", "/")) if len(parts) > 1 else "/"
            return distro, linux_path
    return None


def resolve_dir(arg: str) -> Path:
    p = Path(arg).expanduser()
    # Skip resolve() for UNC paths (\\server\share) — it corrupts them on Windows
    if not str(p).startswith("\\\\"):
        p = p.resolve()
    if not p.is_dir():
        sys.exit(c("red", f"[error] Not a directory: {p}"))
    return p


# ── Git helpers ───────────────────────────────────────────

def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    wsl = _wsl_path(cwd)
    if wsl:
        distro, linux_path = wsl
        actual_cmd = ["wsl", "-d", distro, "git", "-C", linux_path] + cmd[1:]
        result = subprocess.run(
            actual_cmd,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    elif str(cwd).startswith("\\\\"):
        cmd = ["git", "-c", "safe.directory=*"] + cmd[1:]
        result = subprocess.run(
            cmd, cwd=cwd,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    else:
        result = subprocess.run(
            cmd, cwd=cwd,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def find_repo_root(start: Path) -> Path | None:
    """Walk up from start to find the directory containing .git."""
    check = start
    while True:
        if (check / ".git").exists():
            return check
        parent = check.parent
        if parent == check:
            return None
        check = parent


def git_init(repo_dir: Path, dry_run: bool) -> bool:
    print(c("yellow", f"  Initialising git repo in: {repo_dir}"))
    if dry_run:
        print(c("dim", "  [dry-run] skipped"))
        return True
    rc, out, err = _run(["git", "init"], repo_dir)
    if rc != 0:
        print(c("red", f"  [error] git init failed: {err}"))
        return False
    print(c("green", f"  {out or 'Initialized'}"))
    return True


def ensure_lfs_installed(repo_dir: Path, dry_run: bool) -> bool:
    """Run `git lfs install` if lfs hooks are not already active."""
    # filter.lfs.required is set by `git lfs install` — its presence means LFS
    # hooks are wired up. `git lfs status` alone is not a reliable check because
    # it returns 0 whenever git-lfs is on PATH, even before `git lfs install`.
    rc, _, _ = _run(["git", "config", "--get", "filter.lfs.required"], repo_dir)
    if rc == 0:
        return True  # already installed
    print(c("yellow", "  Installing git-lfs hooks..."))
    if dry_run:
        print(c("dim", "  [dry-run] skipped"))
        return True
    rc, out, err = _run(["git", "lfs", "install"], repo_dir)
    if rc != 0:
        print(c("red", f"  [error] git lfs install failed: {err}"))
        print(c("yellow", "  Ensure git-lfs is installed: https://git-lfs.com"))
        return False
    print(c("green", f"  git lfs install: {out or 'done'}"))
    return True


def get_already_tracked(repo_root: Path) -> set[str]:
    """Return the set of patterns already tracked by LFS in .gitattributes."""
    attrs = repo_root / ".gitattributes"
    tracked: set[str] = set()
    if not attrs.exists():
        return tracked
    try:
        for line in attrs.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if "filter=lfs" in line:
                tracked.add(line.split()[0])
    except OSError:
        pass
    return tracked


def lfs_track(pattern: str, repo_root: Path, dry_run: bool) -> bool:
    if dry_run:
        print(c("dim", f"  [dry-run] git lfs track \"{pattern}\""))
        return True
    rc, out, err = _run(["git", "lfs", "track", pattern], repo_root)
    if rc != 0:
        print(c("red", f"  [error] tracking '{pattern}': {err}"))
        return False
    # git lfs track prints "Tracking <pattern>" — show the first line only
    msg = (out or err).splitlines()[0] if (out or err) else "done"
    print(c("green", f"  {msg}"))
    return True


def lfs_pattern_for(file_path: Path) -> str:
    """*.ext for files with an extension; exact filename otherwise."""
    suffix = file_path.suffix   # e.g. '.zip', '.psd', or ''
    return f"*{suffix}" if suffix else file_path.name


# ── Scan ──────────────────────────────────────────────────

def scan_large_files(root: Path, threshold_bytes: int) -> list[Path]:
    large: list[Path] = []
    for dirpath, dirs, files in os.walk(str(root), followlinks=False):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            fpath = Path(dirpath) / fname
            try:
                if fpath.stat().st_size > threshold_bytes:
                    large.append(fpath)
            except OSError:
                continue
    return sorted(large)


# ── Entry point ───────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan a directory for large files and register them with Git LFS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[1] if "Usage:" in __doc__ else "",
    )
    parser.add_argument(
        "dir_path",
        help="Directory to scan (absolute, relative, or WSL UNC path)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without making any changes",
    )
    parser.add_argument(
        "--threshold", type=float, default=SIZE_THRESHOLD_MB, metavar="MB",
        help=f"File size threshold in MB (default: {SIZE_THRESHOLD_MB})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    threshold_bytes = int(args.threshold * 1024 * 1024)
    root = resolve_dir(args.dir_path)

    print(c("bold", "\ngit-lfs-auto"))
    print(f"Directory : {c('cyan', str(root))}")
    print(f"Threshold : {c('cyan', f'{args.threshold} MB  ({threshold_bytes:,} bytes)')}")
    if args.dry_run:
        print(c("yellow", "Mode      : DRY RUN — no changes will be made"))
    print()

    # ── 1. Scan for large files ───────────────────────────
    print("Scanning...", end="", flush=True)
    large_files = scan_large_files(root, threshold_bytes)
    print(f"  {len(large_files)} large file(s) found\n")

    if not large_files:
        print(c("green", "No files exceed the threshold. Nothing to do."))
        return

    for f in large_files:
        try:
            size_mb = f.stat().st_size / (1024 * 1024)
        except OSError:
            size_mb = 0.0
        try:
            rel = f.relative_to(root)
        except ValueError:
            rel = f
        print(f"  {size_mb:7.2f} MB  {rel}")
    print()

    # ── 2. Find or initialise git repo ───────────────────
    repo_root = find_repo_root(root)
    if repo_root is None:
        print(c("yellow", f"No git repo found at or above: {root}"))
        if not git_init(root, args.dry_run):
            sys.exit(1)
        repo_root = root
        print()
    else:
        print(f"Git repo  : {c('cyan', str(repo_root))}\n")

    # ── 3. Ensure git-lfs hooks are installed ─────────────
    if not ensure_lfs_installed(repo_root, args.dry_run):
        sys.exit(1)

    # ── 4. Determine which patterns need tracking ─────────
    already_tracked = get_already_tracked(repo_root)
    patterns: dict[str, list[Path]] = {}   # pattern -> example files

    for f in large_files:
        pat = lfs_pattern_for(f)
        if pat not in already_tracked:
            patterns.setdefault(pat, []).append(f)

    if not patterns:
        print(c("green", "\nAll large-file patterns are already in .gitattributes."))
        return

    print(f"\nTracking {len(patterns)} new pattern(s):")
    all_ok = True
    for pat in sorted(patterns):
        examples = patterns[pat]
        try:
            example_rel = examples[0].relative_to(root)
        except ValueError:
            example_rel = examples[0].name
        print(f"  {c('cyan', pat):<30}  e.g. {example_rel}")
        if not lfs_track(pat, repo_root, args.dry_run):
            all_ok = False

    # ── 5. Stage .gitattributes ───────────────────────────
    if all_ok and not args.dry_run:
        print()
        rc, _, err = _run(["git", "add", ".gitattributes"], repo_root)
        if rc == 0:
            print(c("green", ".gitattributes staged."))
        else:
            print(c("yellow", f"Could not stage .gitattributes: {err}"))

    print()
    if args.dry_run:
        print(c("yellow", "Dry-run complete — no files were modified."))
    elif all_ok:
        print(c("green", "Done. Commit .gitattributes to complete LFS setup."))
        print(c("dim",   '  git commit -m "chore: track large files with Git LFS"'))
    else:
        print(c("red",   "Some patterns could not be tracked — check errors above."))
        sys.exit(1)


if __name__ == "__main__":
    main()
