#!/usr/bin/env python3
"""
@title Init Git Submodules
@description Read .gitmodules and ensure all submodules are properly initialized
@author Ropean, Claude Sonnet (Anthropic)
@version 1.1.0

Automatically parse .gitmodules and handle each submodule based on its current state:
- Directory doesn't exist: clone and register
- Valid git repo with source files: register without cloning (preserves local changes)
- Broken git repo (has .git but no source): remove and re-clone
- Exists but not a git repo: warn and skip (or --force-init to initialize in place)

When submodules are skipped, interactively prompts whether to re-run with --force-init.
Cross-platform compatible: macOS, Linux, Windows, and WSL.

@example
Usage:
    python git-upsert-submodules.py                          # prompt for dir, default cwd
    python git-upsert-submodules.py /path/to/repo            # specify repo root explicitly
    python git-upsert-submodules.py --force-init             # init non-git dirs as submodules
    python git-upsert-submodules.py --force-init /path/to/repo

@requires Python 3.6+
"""

import argparse
import configparser
import os
import subprocess
import shutil
import sys
from pathlib import Path

from path_utils import resolve_path

# ════════════════════════════════════════════════════════════
#  TERMINAL COLORS
# ════════════════════════════════════════════════════════════

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
        "red":      "\033[31m",
        "yellow":   "\033[33m",
        "green":    "\033[32m",
        "cyan":     "\033[36m",
        "bold":     "\033[1m",
        "dim":      "\033[2m",
        "reset":    "\033[0m",
    }
else:
    _C = {k: "" for k in ("red", "yellow", "green", "cyan", "bold", "dim", "reset")}


def run(cmd, cwd=None):
    print(f"  >> {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def is_valid_git_repo(path):
    result = run(["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0


def has_tracked_files(path):
    result = run(["git", "-C", str(path), "ls-files"])
    return result.returncode == 0 and len(result.stdout.strip()) > 0


def parse_gitmodules(filepath):
    config = configparser.ConfigParser()
    config.read(filepath)

    submodules = []
    for section in config.sections():
        if section.startswith("submodule"):
            path = config.get(section, "path", fallback=None)
            url = config.get(section, "url", fallback=None)
            branch = config.get(section, "branch", fallback=None)
            if path and url:
                submodules.append({
                    "name": section,
                    "path": path,
                    "url": url,
                    "branch": branch,
                })
    return submodules


def resolve_repo_root(arg=None):
    if arg:
        repo_root = resolve_path(arg)
    else:
        try:
            user_input = input(
                f"Enter repo directory (press Enter for current directory "
                f"[{_C['cyan']}{Path.cwd()}{_C['reset']}]): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            user_input = ""
            print()
        repo_root = resolve_path(user_input) if user_input else Path.cwd().resolve()

    if not (repo_root / ".gitmodules").exists():
        print(f"{_C['red']}ERROR:{_C['reset']} .gitmodules not found in {repo_root}")
        sys.exit(1)

    return repo_root


def register_existing_repo(repo_root, sub_path, url):
    """Register an existing valid git repo as a submodule without cloning."""
    result = run(["git", "submodule", "add", url, str(sub_path)], cwd=str(repo_root))
    if result.returncode == 0:
        print(f"  OK: registered successfully.")
        return True

    stderr = result.stderr.strip()
    if "already exists in the index" in stderr:
        print(f"  Already registered as submodule.")
        return True

    # git submodule add may fail for existing dirs; fall back to direct index update
    print(f"  Note: 'git submodule add' failed ({stderr}). Trying direct registration...")
    result = run(["git", "add", str(sub_path)], cwd=str(repo_root))
    if result.returncode == 0:
        print(f"  OK: registered via 'git add'.")
        return True

    print(f"  FAILED: could not register. {result.stderr.strip()}")
    return False


def clone_submodule(repo_root, sub_path, url, branch=None):
    cmd = ["git", "submodule", "add"]
    if branch:
        cmd += ["-b", branch]
    cmd += [url, str(sub_path)]
    result = run(cmd, cwd=str(repo_root))
    if result.returncode != 0:
        print(f"  FAILED: {result.stderr.strip()}")
        return False
    print(f"  OK: cloned successfully.")
    return True


def init_and_register(repo_root, sub_path, full_path, url):
    """Initialize a non-git directory as a git repo, add remote, commit, and register."""
    print(f"  Initializing as git repo with remote {url} ...")

    result = run(["git", "init"], cwd=str(full_path))
    if result.returncode != 0:
        print(f"  FAILED: git init failed. {result.stderr.strip()}")
        return False

    result = run(["git", "remote", "add", "origin", url], cwd=str(full_path))
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "already exists" not in stderr:
            print(f"  FAILED: git remote add failed. {stderr}")
            return False

    result = run(["git", "add", "."], cwd=str(full_path))
    if result.returncode != 0:
        print(f"  FAILED: git add failed. {result.stderr.strip()}")
        return False

    result = run(["git", "commit", "-m", "Initial commit"], cwd=str(full_path))
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "nothing to commit" not in stderr:
            print(f"  FAILED: git commit failed. {stderr}")
            return False

    return register_existing_repo(repo_root, sub_path, url)


def process_submodules(repo_root, force_init=False):
    """Run the submodule upsert logic and return results dict."""
    submodules = parse_gitmodules(repo_root / ".gitmodules")
    print(f"Found {len(submodules)} submodule(s) in .gitmodules\n")

    results = {"ok": [], "skipped": [], "failed": []}

    for sub in submodules:
        rel_path = sub["path"]
        full_path = repo_root / rel_path
        url = sub["url"]
        branch = sub.get("branch")
        print(f"--- [{sub['name']}] path={rel_path} ---")

        if not full_path.exists():
            print(f"  Directory does not exist. Cloning...")
            if clone_submodule(repo_root, rel_path, url, branch):
                results["ok"].append(rel_path)
            else:
                results["failed"].append(rel_path)

        elif full_path.is_dir() and (full_path / ".git").exists():
            if is_valid_git_repo(full_path) and has_tracked_files(full_path):
                print(f"  Valid git repo with source files. Registering without cloning...")
                if register_existing_repo(repo_root, rel_path, url):
                    results["ok"].append(rel_path)
                else:
                    results["failed"].append(rel_path)
            else:
                print(f"  Broken git repo (no source). Removing and re-cloning...")
                shutil.rmtree(full_path)
                if clone_submodule(repo_root, rel_path, url, branch):
                    results["ok"].append(rel_path)
                else:
                    results["failed"].append(rel_path)

        elif full_path.is_dir():
            if force_init:
                print(f"  Directory exists but is not a git repo. --force-init: initializing...")
                if init_and_register(repo_root, rel_path, full_path, url):
                    results["ok"].append(rel_path)
                else:
                    results["failed"].append(rel_path)
            else:
                print(f"  {_C['yellow']}WARNING:{_C['reset']} Directory exists but is not a git repo. Skipping to avoid data loss.")
                print(f"  Hint: use --force-init to initialize it as a submodule.")
                results["skipped"].append(rel_path)

        else:
            print(f"  {_C['yellow']}WARNING:{_C['reset']} Path exists but is not a directory. Skipping.")
            results["skipped"].append(rel_path)

        print()

    return results


def print_summary(results):
    print("=" * 50)
    print(f"  {_C['green']}OK:{_C['reset']}      {len(results['ok'])}")
    print(f"  {_C['yellow']}Skipped:{_C['reset']} {len(results['skipped'])}")
    print(f"  {_C['red']}Failed:{_C['reset']}  {len(results['failed'])}")
    if results["failed"]:
        print(f"  Failed items: {', '.join(results['failed'])}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Init git submodules from .gitmodules")
    parser.add_argument("repo", nargs="?", default=None, help="repo root (default: prompt / cwd)")
    parser.add_argument("--force-init", action="store_true",
                        help="initialize non-git directories as submodules instead of skipping")
    args = parser.parse_args()

    repo_root = resolve_repo_root(args.repo)
    print(f"Repo root: {_C['bold']}{repo_root}{_C['reset']}\n")

    results = process_submodules(repo_root, force_init=args.force_init)
    print_summary(results)

    if results["skipped"] and not args.force_init:
        print(f"\n{_C['yellow']}{len(results['skipped'])} submodule(s) were skipped.{_C['reset']}")
        try:
            answer = input(
                f"Re-run with {_C['cyan']}--force-init{_C['reset']} to initialize them? "
                f"[{_C['green']}Y{_C['reset']}/n]: "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
            print()

        if answer in ("", "y", "yes"):
            print(f"\n{_C['bold']}Re-running with --force-init ...{_C['reset']}\n")
            results = process_submodules(repo_root, force_init=True)
            print_summary(results)

    print(f"\nRun {_C['dim']}git submodule status{_C['reset']} to verify.")


if __name__ == "__main__":
    main()