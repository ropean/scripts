#!/usr/bin/env python3
"""
@title git-clean-ignored
@description Scan a directory for Git repos and clean all gitignored files, safely.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Scans every immediate subdirectory of <dir> for Git repositories, then removes
files matched by .gitignore rules via `git clean -fdX`, while preserving
environment and secrets files (.env, credentials, keys, etc.).

Large directories such as node_modules are deleted in bulk before git clean
runs, using a long-path-safe method (\\\\?\\ prefix on Windows, rm -rf in WSL)
to avoid the 260-character NTFS path limit common with pnpm/yarn workspaces.

Repos with submodules are handled by discovering submodule paths via
`git submodule foreach` and cleaning each one individually, so every level
of nesting gets the same long-path-safe treatment.

Supports Windows absolute paths, relative paths, and WSL UNC paths
(\\\\wsl.localhost\\<distro>\\... or \\\\wsl$\\<distro>\\...).
Running without arguments launches an interactive setup wizard.

@example
    python git-clean-ignored.py "D:\\Git"
    python git-clean-ignored.py "D:\\Git" --dry-run
    python git-clean-ignored.py "D:\\Git" --recursive --depth 2 --submodules
    python git-clean-ignored.py "\\\\wsl.localhost\\Ubuntu\\home\\user\\projects"
    python git-clean-ignored.py   # interactive wizard
"""

from __future__ import annotations

# ════════════════════════════════════════════════════════════
#  USER CONFIG
# ════════════════════════════════════════════════════════════

# Files matching these gitignore-style patterns are NEVER deleted,
# even when .gitignore would otherwise match them.
# A pattern with no '/' matches in any subdirectory of the repo.
PROTECTED_PATTERNS: list[str] = [
    # dotenv variants
    ".env",
    ".env.*",
    "*.env",
    ".envrc",           # direnv
    ".env.local",
    ".env.*.local",
    # secrets / credentials
    "secrets",
    "secrets.*",
    "*.secret",
    "*.secrets",
    ".secret",
    ".secrets",
    "secret.yml",
    "secret.yaml",
    "credentials",
    "credentials.*",
    ".credentials",
    "*.credentials",
    # common secrets paths
    "config/secrets*",
    "config/credentials*",
    ".vault-token",     # HashiCorp Vault
    # key/cert files
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
]

# Directories skipped while searching for git repos
_SKIP_DIRS: set[str] = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# Directories deleted in bulk BEFORE git clean to avoid Windows long-path errors.
# These are typically gitignored and can contain deeply nested paths that exceed
# the 260-character Windows path limit (e.g. pnpm's node_modules/.pnpm/...).
BULK_DELETE_DIRS: list[str] = [
    "node_modules",
    ".next",
    ".nuxt",
    ".turbo",
    ".svelte-kit",
    ".output",
    "dist",
    "build",
    ".cache",
    ".parcel-cache",
    ".vite",
]

# ════════════════════════════════════════════════════════════
#  END OF USER CONFIG
# ════════════════════════════════════════════════════════════

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ── Terminal colors ───────────────────────────────────────

def _supports_color() -> bool:
    if os.environ.get("FORCE_COLOR") or os.environ.get("COLORTERM"):
        return True
    term = os.environ.get("TERM", "")
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
            rest = s[len(prefix):]          # "Ubuntu\home\user\projects"
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


def is_git_repo(path: Path) -> bool:
    """True if path contains a .git entry (file or directory, covering submodules)."""
    return (path / ".git").exists()


# ── Repo discovery ────────────────────────────────────────

def find_git_repos(root: Path, recursive: bool, max_depth: int = 3) -> list[Path]:
    """
    Return git repo roots found inside root.

    Without --recursive: only immediate children (depth 1).
    With --recursive: descend up to max_depth levels, never entering a found repo
    or any directory in _SKIP_DIRS.
    """
    repos: list[Path] = []

    def _scan(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(directory.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if not entry.is_dir() or entry.name in _SKIP_DIRS:
                continue
            if is_git_repo(entry):
                repos.append(entry)
                # never descend into a found repo
            elif recursive:
                _scan(entry, depth + 1)

    _scan(root, 1)
    return repos


# ── Bulk directory deletion (long-path safe) ─────────────

def _rmtree_windows(path: Path) -> None:
    """
    Delete a directory tree on Windows, bypassing the 260-char path limit
    by using the \\\\?\\ extended-length path prefix.
    Falls back to shutil.rmtree if the prefix trick isn't needed / doesn't apply.
    """
    # \\?\ prefix only works with absolute, non-UNC paths
    p = str(path)
    if not p.startswith("\\\\"):
        long_p = "\\\\?\\" + p if not p.startswith("\\\\?\\") else p
        subprocess.run(
            ["cmd", "/c", "rmdir", "/s", "/q", long_p],
            capture_output=True,
        )
    else:
        shutil.rmtree(str(path), ignore_errors=True)


def _rmtree_wsl(linux_path: str, distro: str) -> None:
    """Delete a directory inside WSL using `rm -rf`."""
    subprocess.run(
        ["wsl", "-d", distro, "rm", "-rf", "--", linux_path],
        capture_output=True,
    )


def _is_gitignored(name: str, repo: Path) -> bool:
    """Ask git whether a path is ignored (so we don't delete tracked dirs)."""
    rc, _, _ = _run(["git", "check-ignore", "-q", name], repo)
    return rc == 0


def bulk_delete_ignored_dirs(repo: Path, dry_run: bool, max_depth: int = 4) -> None:
    """
    Recursively walk `repo` (up to max_depth levels) looking for any directory
    named in BULK_DELETE_DIRS.  Each candidate is verified as gitignored before
    deletion.  Stops descending into a directory once it is deleted.

    Handles both Windows long-path (\\\\?\\) and WSL paths.
    """
    bulk_names = set(BULK_DELETE_DIRS)
    wsl = _wsl_path(repo)

    if wsl:
        # WSL: use `find` to locate all candidates in one shot, then rm -rf each.
        distro, linux_repo = wsl
        for name in bulk_names:
            result = subprocess.run(
                [
                    "wsl", "-d", distro,
                    "find", linux_repo,
                    "-maxdepth", str(max_depth),
                    "-name", name, "-type", "d",
                    "-not", "-path", "*/.git/*",
                ],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            for linux_target in result.stdout.splitlines():
                linux_target = linux_target.strip()
                if not linux_target:
                    continue
                # Derive relative path for git check-ignore
                rel = linux_target[len(linux_repo):].lstrip("/").replace("/", os.sep)
                if not _is_gitignored(rel, repo):
                    continue
                if dry_run:
                    print(c("dim", f"  [dry-run] would delete {rel}{os.sep}"))
                    continue
                print(c("yellow", f"  Deleting {rel}{os.sep}  (long-path safe)"), end="", flush=True)
                _rmtree_wsl(linux_target, distro)
                print(c("green", "  done"))
    else:
        # Windows: walk the tree ourselves so we can use \\?\\ for deletion.
        _skip = {".git"}

        def _walk(directory: Path, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                entries = sorted(directory.iterdir())
            except (PermissionError, OSError):
                return
            for entry in entries:
                if not entry.is_dir():
                    continue
                if entry.name in bulk_names:
                    try:
                        rel = str(entry.relative_to(repo))
                    except ValueError:
                        rel = entry.name
                    if not _is_gitignored(rel.replace("\\", "/"), repo):
                        continue
                    if dry_run:
                        print(c("dim", f"  [dry-run] would delete {rel}{os.sep}"))
                        continue
                    print(c("yellow", f"  Deleting {rel}{os.sep}  (long-path safe)"), end="", flush=True)
                    _rmtree_windows(entry)
                    print(c("green", "  done"))
                    # don't descend into a directory we just deleted
                elif entry.name not in _skip:
                    _walk(entry, depth + 1)

        _walk(repo, 1)


# ── Submodule discovery ───────────────────────────────────

def get_submodule_paths(repo: Path) -> list[Path]:
    """
    Return absolute paths to all submodules (recursive) inside repo.
    Uses `git submodule foreach --recursive` so git handles .gitmodules parsing.
    Works for both normal Windows paths and WSL UNC paths.
    """
    rc, out, _ = _run(
        ["git", "submodule", "foreach", "--quiet", "--recursive", "echo $displaypath"],
        repo,
    )
    if rc != 0 or not out:
        return []
    paths: list[Path] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # $displaypath uses forward slashes; Path() handles them on Windows too
        sub = repo / Path(line)
        if sub.is_dir() or _wsl_path(repo):  # WSL: trust git output, skip is_dir
            paths.append(sub)
    return paths


# ── git clean ─────────────────────────────────────────────

def build_clean_cmd(dry_run: bool) -> list[str]:
    """Build the `git clean` command with protected-pattern exclusions."""
    cmd = ["git", "clean", "-fdX"]
    if dry_run:
        cmd.append("-n")   # --dry-run: list files, don't delete
    for pattern in PROTECTED_PATTERNS:
        cmd += ["-e", pattern]
    # Bulk-delete dirs are handled separately before git clean
    for name in BULK_DELETE_DIRS:
        cmd += ["-e", name]
    return cmd


def _clean_one(repo: Path, dry_run: bool, indent: str = "  ") -> bool:
    """Run bulk delete + git clean on a single repo directory."""
    bulk_delete_ignored_dirs(repo, dry_run)

    cmd = build_clean_cmd(dry_run)
    rc, out, err = _run(cmd, repo)

    if rc != 0:
        print(c("red", f"{indent}[error] git clean failed: {err or out}"))
        return False

    if not out:
        print(c("dim", f"{indent}(nothing left to clean)"))
        return True

    for line in out.splitlines():
        prefix = f"{indent}[dry-run] " if dry_run else indent
        print(c("dim" if dry_run else "green", f"{prefix}{line}"))
    return True


def clean_repo(repo: Path, dry_run: bool, recurse_submodules: bool) -> bool:
    """
    Clean a repository:
      1. Bulk-delete gitignored large directories (long-path safe).
      2. git clean -fdX for everything else.
      3. If recurse_submodules, repeat for every submodule.
    """
    ok = _clean_one(repo, dry_run)

    if not recurse_submodules:
        return ok

    submodules = get_submodule_paths(repo)
    if not submodules:
        return ok

    print(c("dim", f"  Submodules ({len(submodules)}):"))
    for sub in submodules:
        try:
            label = sub.relative_to(repo)
        except ValueError:
            label = sub
        print(c("bold", f"    [{label}]"))
        if not _clean_one(sub, dry_run, indent="      "):
            ok = False
        print()

    return ok


# ── Interactive prompt helpers ────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    hint = f" [{c('dim', default)}]" if default else ""
    try:
        val = input(f"  {prompt}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val or default


def _ask_yn(prompt: str, default: bool = False) -> bool:
    hint = c("dim", "Y/n" if default else "y/N")
    try:
        val = input(f"  {prompt} [{hint}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return default if not val else val in ("y", "yes", "1")


def interactive_prompt() -> argparse.Namespace:
    """Walk the user through all options when no CLI args are given."""
    print(c("bold", "\ngit-clean-ignored — interactive setup\n"))

    # 1. Directory
    dir_path = _ask("Directory to scan (absolute, relative, or WSL UNC path)", ".")

    # 2. Recursive
    recursive = _ask_yn("Scan subdirectories recursively?", default=False)

    # 3. Depth (only relevant when recursive)
    depth = 3
    if recursive:
        raw = _ask("Max recursion depth", "3")
        try:
            depth = int(raw)
        except ValueError:
            print(c("yellow", "  Invalid number, using default 3."))
            depth = 3

    # 4. Submodules
    submodules = _ask_yn("Also clean inside submodules?", default=True)

    # 5. Dry-run — last, and default True so users don't accidentally nuke things
    dry_run = _ask_yn("Dry-run first? (recommended)", default=True)

    print()
    import argparse as _ap
    ns = _ap.Namespace(
        dir_path=dir_path,
        recursive=recursive,
        depth=depth,
        submodules=submodules,
        dry_run=dry_run,
    )
    return ns


# ── Entry point ───────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean gitignored files from Git repos found inside a directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[1] if "Usage:" in __doc__ else "",
    )
    parser.add_argument(
        "dir_path",
        help="Directory to scan (absolute, relative, or WSL UNC path)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be removed without deleting anything",
    )
    parser.add_argument(
        "--recursive", action="store_true",
        help="Descend into subdirectories to find git repos (default depth: 3)",
    )
    parser.add_argument(
        "--depth", type=int, default=3, metavar="N",
        help="Max recursion depth when using --recursive (default: 3)",
    )
    parser.add_argument(
        "--submodules", action="store_true",
        help="Also clean inside submodules (reads .gitmodules and cleans each submodule separately)",
    )
    return parser.parse_args()


def main() -> None:
    if len(sys.argv) == 1:
        args = interactive_prompt()
    else:
        args = parse_args()
    root = resolve_dir(args.dir_path)

    print(c("bold", "\ngit-clean-ignored"))
    print(f"Directory : {c('cyan', str(root))}")
    if args.recursive:
        print(f"Recursive : depth ≤ {c('cyan', str(args.depth))}")
    if args.submodules:
        print(f"Submodules: {c('cyan', 'will be cleaned')}")
    if args.dry_run:
        print(c("yellow", "Mode      : DRY RUN — no files will be deleted"))
    print()

    # ── 1. Discover repos ─────────────────────────────────
    # If the given directory is itself a repo, clean it directly.
    if is_git_repo(root):
        repos = [root]
    else:
        repos = find_git_repos(root, args.recursive, args.depth)

    if not repos:
        print(c("yellow", "No git repositories found in the immediate subdirectories."))
        if not args.recursive:
            print(c("dim", "Tip: use --recursive to search at any depth."))
        return

    print(f"Found {c('cyan', str(len(repos)))} git repo(s):\n")
    for r in repos:
        try:
            rel = r.relative_to(root)
        except ValueError:
            rel = r
        print(f"  {rel}")
    print()

    # ── 2. Protected-patterns summary ─────────────────────
    print(c("dim", f"Protected patterns ({len(PROTECTED_PATTERNS)}): "
            + "  ".join(PROTECTED_PATTERNS[:6])
            + ("  ..." if len(PROTECTED_PATTERNS) > 6 else "")))
    print()

    # ── 3. Clean each repo ────────────────────────────────
    ok_count = 0
    fail_count = 0

    for repo in repos:
        try:
            rel = repo.relative_to(root)
        except ValueError:
            rel = repo
        print(c("bold", f"[{rel}]"))
        if clean_repo(repo, args.dry_run, args.submodules):
            ok_count += 1
        else:
            fail_count += 1
        print()

    # ── 4. Summary ────────────────────────────────────────
    if args.dry_run:
        print(c("yellow", f"Dry-run complete. {ok_count} repo(s) checked, {fail_count} error(s)."))
    elif fail_count == 0:
        print(c("green", f"Done. {ok_count} repo(s) cleaned successfully."))
    else:
        print(c("red", f"Finished with errors: {ok_count} ok, {fail_count} failed."))
        sys.exit(1)


if __name__ == "__main__":
    main()
