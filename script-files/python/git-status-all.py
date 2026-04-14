#!/usr/bin/env python3
"""
@title git-status-all
@description Check Git status for every repository under a root directory.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Runs `git fetch --all` in parallel first (use --no-fetch to skip), then shows
status for all subdirectories — git repos and non-git dirs alike.
Output includes branch, ahead/behind remote, staged/unstaged/untracked counts,
and can be saved to a timestamped report file.

@example
    python git-status-all.py
    python git-status-all.py "D:\\Git"
    python git-status-all.py "D:\\Git" --no-fetch
    python git-status-all.py "D:\\Git" -o report.txt
"""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ════════════════════════════════════════════════════════════
#  USER CONFIG
# ════════════════════════════════════════════════════════════

PLATFORM_DEFAULTS = {
    "win32":  r"D:\Git",
    "darwin": "~/Git",
    "linux":  "~/Git",  # includes WSL
}

# ════════════════════════════════════════════════════════════
#  END OF USER CONFIG
# ════════════════════════════════════════════════════════════

FETCH_WORKERS = 8
COL_NAME      = 30
COL_BRANCH    = 22


# ── Terminal colors ───────────────────────────────────────

def _supports_color() -> bool:
    # TERM set and non-dumb covers Git Bash (isatty() can be False there)
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
        "darkgray": "\033[90m",
        "reset":    "\033[0m",
    }
else:
    _C = {k: "" for k in ("red", "yellow", "green", "cyan", "bold", "dim", "darkgray", "reset")}


def c(color: str, text: str) -> str:
    return f"{_C[color]}{text}{_C['reset']}"


# ── Path helpers ──────────────────────────────────────────

def resolve_root(arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser()
    else:
        key = sys.platform if sys.platform in PLATFORM_DEFAULTS else "linux"
        p = Path(PLATFORM_DEFAULTS[key]).expanduser()
    # Skip resolve() for UNC paths (\\server\share) — it corrupts them on Windows
    if not str(p).startswith("\\\\"):
        p = p.resolve()
    if not p.is_dir():
        sys.exit(f"Error: directory not found: {p}")
    return p


def scan_dirs(root: Path) -> tuple[list[Path], list[Path]]:
    """Return (git_repos, non_git_dirs) — both sorted by name, dotfiles excluded."""
    repos, others = [], []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        (repos if (entry / ".git").exists() else others).append(entry)
    return repos, others


# ── Git helpers ───────────────────────────────────────────

def _wsl_path(cwd: Path) -> tuple[str, str] | None:
    """If cwd is a WSL UNC path, return (distro, linux_path); else None."""
    s = str(cwd)
    for prefix in ("\\\\wsl.localhost\\", "\\\\wsl$\\"):
        if s.startswith(prefix):
            rest = s[len(prefix):]          # "Ubuntu\home\robot-u\git\folio"
            parts = rest.split("\\", 1)
            distro = parts[0]
            linux_path = ("/" + parts[1].replace("\\", "/")) if len(parts) > 1 else "/"
            return distro, linux_path
    return None


def _run(
    cmd: list[str], cwd: Path, extra_env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    env = {**os.environ, **(extra_env or {})}
    wsl = _wsl_path(cwd)
    if wsl:
        # Run git inside WSL so it uses Linux git semantics (no fileMode/CRLF/
        # filename-encoding mismatches that Windows git introduces on WSL paths).
        distro, linux_path = wsl
        actual_cmd = ["wsl", "-d", distro, "git", "-C", linux_path] + cmd[1:]
        result = subprocess.run(
            actual_cmd, env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    elif str(cwd).startswith("\\\\"):
        # Generic UNC path — bypass dubious-ownership check
        cmd = ["git", "-c", "safe.directory=*"] + cmd[1:]
        result = subprocess.run(
            cmd, cwd=cwd, env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    else:
        result = subprocess.run(
            cmd, cwd=cwd, env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def fetch_repo(repo: Path) -> tuple[Path, str]:
    """Fetch all remotes; return (repo, error_or_empty)."""
    rc, _, err = _run(
        ["git", "fetch", "--all", "--quiet", "--no-progress"],
        repo,
        extra_env={"GIT_TERMINAL_PROMPT": "0"},
    )
    return repo, (err if rc != 0 else "")


def get_repo_status(repo: Path) -> dict:
    _, branch, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)

    _, porcelain, _ = _run(["git", "status", "--porcelain"], repo)
    dirty_files = [ln for ln in porcelain.splitlines() if ln.strip()]

    _, stash_out, _ = _run(["git", "stash", "list"], repo)
    stash_count = len(stash_out.splitlines()) if stash_out else 0

    ahead = behind = 0
    _, upstream, _ = _run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        repo,
    )
    has_upstream = upstream and "fatal" not in upstream.lower() and "no upstream" not in upstream.lower()
    if has_upstream:
        _, ab_out, _ = _run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
            repo,
        )
        parts = ab_out.split()
        if len(parts) == 2:
            try:
                ahead, behind = int(parts[0]), int(parts[1])
            except ValueError:
                pass
    else:
        upstream = None

    _, log_out, _ = _run(["git", "log", "-1", "--format=%h %s (%cr)"], repo)

    return {
        "repo":        repo,
        "branch":      branch or "?",
        "dirty_files": dirty_files,
        "stash_count": stash_count,
        "upstream":    upstream,
        "ahead":       ahead,
        "behind":      behind,
        "last_commit": log_out,
    }


def row_color(info: dict) -> str:
    if info["dirty_files"]:
        return "red"
    if info["ahead"] or info["behind"]:
        return "yellow"
    return "dim"


def status_label(info: dict) -> str:
    parts = []
    if info["dirty_files"]:
        parts.append(f"{len(info['dirty_files'])} dirty")
    if info["behind"]:
        parts.append(f"{info['behind']} behind")
    if info["ahead"]:
        parts.append(f"{info['ahead']} ahead")
    if info["stash_count"]:
        parts.append(f"{info['stash_count']} stashed")
    return ", ".join(parts) if parts else "clean"


# ── Display ───────────────────────────────────────────────

def print_repo_row(info: dict) -> None:
    stash = f"  [{info['stash_count']} stashed]" if info["stash_count"] else ""
    label = status_label(info)
    # Build plain text first so padding is correct, then colorize the whole row
    row = f"  {info['repo'].name:<{COL_NAME}}  {info['branch']:<{COL_BRANCH}}  {label}{stash}"
    print(c(row_color(info), row))


def print_nongit_row(d: Path) -> None:
    row = f"  {d.name:<{COL_NAME}}  {'(not git)':<{COL_BRANCH}}  --"
    print(c("darkgray", row))


# ── Report ────────────────────────────────────────────────

def save_report(results: list[dict], non_git: list[Path], root: Path, out: Path) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean   = [r for r in results if status_label(r) == "clean"]
    unclean = [r for r in results if r not in clean]

    md: list[str] = [
        "# Git Status Report",
        "",
        f"- **Date**: {ts}",
        f"- **Root**: `{root}`",
        f"- **Git repos**: {len(results)} scanned — "
        f"{len(clean)} clean, {len(unclean)} need attention",
        f"- **Non-git dirs**: {len(non_git)}",
        "",
        f"## Needs Attention ({len(unclean)} repos)",
        "",
    ]

    if unclean:
        for r in unclean:
            md.append(f"### `{r['repo'].name}` — {status_label(r)}")
            md.append(f"- Branch: `{r['branch']}`")
            if r["upstream"]:
                md.append(f"- Upstream: `{r['upstream']}`  "
                           f"(ahead {r['ahead']}, behind {r['behind']})")
            else:
                md.append("- Upstream: none")
            if r["dirty_files"]:
                md.append(f"- Dirty files ({len(r['dirty_files'])}):")
                for f in r["dirty_files"][:20]:
                    md.append(f"  - `{f}`")
                if len(r["dirty_files"]) > 20:
                    md.append(f"  - ... and {len(r['dirty_files']) - 20} more")
            if r["stash_count"]:
                md.append(f"- Stashed entries: {r['stash_count']}")
            if r["last_commit"]:
                md.append(f"- Last commit: {r['last_commit']}")
            md.append("")
    else:
        md.append("All repos are clean.\n")

    md += [f"## Clean ({len(clean)} repos)", ""]
    for r in clean:
        up = f"(`{r['upstream']}`)" if r["upstream"] else "(no upstream)"
        md.append(f"- `{r['repo'].name}` on `{r['branch']}` {up}")
    md.append("")

    if non_git:
        md += [f"## Non-git directories ({len(non_git)})", ""]
        for d in non_git:
            md.append(f"- `{d.name}`")
        md.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md), encoding="utf-8")
    print(c("green", f"Report saved: {out}"))


# ── Entry point ───────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Git status for all directories under a root."
    )
    parser.add_argument(
        "git_dir", nargs="?",
        help="Root directory (default: platform-specific)",
    )
    parser.add_argument(
        "--no-fetch", action="store_true",
        help="Skip git fetch before checking status",
    )
    parser.add_argument(
        "-o", "--output",
        default=None, metavar="FILE",
        help="Save a Markdown report to this file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = resolve_root(args.git_dir)

    print(c("bold", "\ngit-status-all"))
    print(f"Scanning: {c('cyan', str(root))}\n")

    repos, non_git = scan_dirs(root)
    if not repos and not non_git:
        sys.exit("No directories found.")

    # ── Fetch ─────────────────────────────────────────────
    fetch_errors: dict[Path, str] = {}
    if repos and not args.no_fetch:
        print(f"Fetching {len(repos)} repos", end="", flush=True)
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
            futures = {pool.submit(fetch_repo, r): r for r in repos}
            for future in as_completed(futures):
                repo, err = future.result()
                print(".", end="", flush=True)
                if err:
                    fetch_errors[repo] = err
        # '\r' + spaces clears any stray progress text git may have written
        # directly to the console on Windows, then newline to move past it
        sys.stdout.write("\r" + " " * 72 + "\r")
        sys.stdout.flush()
        print("done\n")

    # ── Status + display ──────────────────────────────────
    # Merge repos and non-git dirs into one sorted list for display
    repo_map: dict[str, dict] = {}
    for repo in repos:
        repo_map[repo.name] = get_repo_status(repo)

    non_git_names = {d.name for d in non_git}
    all_names = sorted(repo_map.keys() | non_git_names, key=str.lower)

    results: list[dict] = []
    for name in all_names:
        if name in repo_map:
            info = repo_map[name]
            results.append(info)
            print_repo_row(info)
        else:
            print_nongit_row(root / name)

    # ── Summary ───────────────────────────────────────────
    clean   = [r for r in results if status_label(r) == "clean"]
    dirty   = [r for r in results if r["dirty_files"]]
    sync    = [r for r in results if not r["dirty_files"] and (r["ahead"] or r["behind"])]

    print(f"\n{'-' * 60}")
    print(f"  Repos:    {len(results)}  (+{len(non_git)} not git)")
    print(c("dim",    f"  Clean:    {len(clean)}"))
    if sync:
        print(c("yellow", f"  Sync:     {len(sync)}"))
    if dirty:
        print(c("red",    f"  Dirty:    {len(dirty)}"))

    if fetch_errors:
        print(c("yellow", f"\n  Fetch errors ({len(fetch_errors)}):"))
        for repo, err in fetch_errors.items():
            print(c("yellow", f"    {repo.name}: {err[:80]}"))

    if args.output:
        save_report(results, non_git, root, Path(args.output))


if __name__ == "__main__":
    main()
