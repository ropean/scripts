#!/usr/bin/env python3
"""
@title Init Git Submodules
@description Read .gitmodules and ensure all submodules are properly initialized
@author Ropean
@version 1.0.0

Automatically parse .gitmodules and handle each submodule based on its current state:
- Directory doesn't exist: clone and register
- Valid git repo with source files: register without cloning (preserves local changes)
- Broken git repo (has .git but no source): remove and re-clone
- Exists but not a git repo: warn and skip to avoid data loss

Cross-platform compatible: macOS, Linux, Windows, and WSL.

@example
Usage:
    python git-upsert-submodules.py                  # use script's own directory
    python git-upsert-submodules.py /path/to/repo    # specify repo root explicitly

@requires Python 3.6+
"""

import configparser
import subprocess
import shutil
import sys
from pathlib import Path


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
        repo_root = Path(arg).resolve()
    else:
        repo_root = Path(__file__).resolve().parent

    if not (repo_root / ".gitmodules").exists():
        print(f"ERROR: .gitmodules not found in {repo_root}")
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


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    repo_root = resolve_repo_root(arg)

    print(f"Repo root: {repo_root}\n")

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
            print(f"  WARNING: Directory exists but is not a git repo. Skipping to avoid data loss.")
            results["skipped"].append(rel_path)

        else:
            print(f"  WARNING: Path exists but is not a directory. Skipping.")
            results["skipped"].append(rel_path)

        print()

    print("=" * 50)
    print(f"  OK:      {len(results['ok'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Failed:  {len(results['failed'])}")
    if results["failed"]:
        print(f"  Failed items: {', '.join(results['failed'])}")
    print("=" * 50)
    print("\nRun 'git submodule status' to verify.")


if __name__ == "__main__":
    main()