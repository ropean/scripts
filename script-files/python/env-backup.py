#!/usr/bin/env python3
"""
@title env-backup
@description Back up .env files found via Everything CLI (es.exe) into env-files/.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Runs:  es.exe wfn:.env !path:win-dotfiles
and copies results into env-files/, organised by project name.

@example
    python scripts/env-backup.py [--es-path PATH] [--query QUERY] [-o DIR] [--dry-run]

Options:
    --es-path PATH   Path to es.exe (auto-detected if omitted)
    --query QUERY    Everything search query
    -o / --output    Target directory (default: env-files/ in repo root)
    --dry-run        Show what would be copied without copying

@requires Everything (es.exe)
"""

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT    = SCRIPTS_DIR.parent
DEFAULT_OUT  = REPO_ROOT / "env-files"
DEFAULT_QUERY = "wfn:.env !path:win-dotfiles"

ES_CANDIDATE_PATHS = [
    REPO_ROOT / "bin" / "es.exe",
    Path("C:/Program Files/Everything/es.exe"),
    Path("C:/Program Files (x86)/Everything/es.exe"),
]

EXCLUDE_PATTERNS  = ["/scoop/", "/.vscode/", "/.cursor/", "appdata/local", "$recycle.bin"]
COMMON_CONFIG_DIRS = {"env", "config", "configs", ".config", "environments", "settings"}


# ── Everything ────────────────────────────────────────────────────────────────

def find_es() -> Path | None:
    """Locate es.exe: PATH first, then common install locations."""
    in_path = shutil.which("es") or shutil.which("es.exe")
    if in_path:
        return Path(in_path)
    for p in ES_CANDIDATE_PATHS:
        if p.exists():
            return p
    return None


def query_everything(es: Path, query: str) -> list[str]:
    cmd = [str(es)] + shlex.split(query)
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if not stderr or "IPC" in stderr or "Everything" in stderr:
            print("[error] Cannot connect to Everything — is it running?", file=sys.stderr)
        else:
            print(f"[error] es.exe: {stderr}", file=sys.stderr)
        sys.exit(1)
    return [l.strip() for l in result.stdout.splitlines() if l.strip()]


# ── File helpers ──────────────────────────────────────────────────────────────

def should_exclude(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return any(pat in normalized for pat in EXCLUDE_PATTERNS)


def project_name(src: Path) -> str:
    parent = src.parent
    if parent.name.lower() in COMMON_CONFIG_DIRS:
        return parent.parent.name
    return parent.name


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Back up .env files via Everything CLI (es.exe)."
    )
    p.add_argument("--es-path", metavar="PATH",
                   help="Path to es.exe (auto-detected if omitted)")
    p.add_argument("--query", default=DEFAULT_QUERY,
                   help=f"Everything search query (default: {DEFAULT_QUERY!r})")
    p.add_argument("-o", "--output", default=str(DEFAULT_OUT), metavar="DIR",
                   help=f"Target directory (default: {DEFAULT_OUT.name}/)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print actions without copying")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ── Resolve es.exe ────────────────────────────────────────────────────────
    if args.es_path:
        es = Path(args.es_path)
        if not es.exists():
            print(f"[error] es.exe not found at: {es}", file=sys.stderr)
            sys.exit(1)
    else:
        es = find_es()
        if es is None:
            print(
                "[error] es.exe not found.\n"
                "  • Ensure Everything is installed and es.exe is in PATH, or\n"
                "  • specify its location:  --es-path \"C:\\...\\es.exe\"",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"[es]    {es}",       file=sys.stderr)
    print(f"[query] {args.query}", file=sys.stderr)

    # ── Query ─────────────────────────────────────────────────────────────────
    paths = query_everything(es, args.query)
    print(f"[found] {len(paths)} file(s)\n", file=sys.stderr)

    out_dir = Path(args.output)
    ok = skip = fail = 0

    for raw in paths:
        src = Path(raw)

        if should_exclude(raw):
            print(f"  skip  {raw}", file=sys.stderr)
            skip += 1
            continue

        name = project_name(src)
        dst  = out_dir / name / src.name

        if args.dry_run:
            print(f"  dry   {src}  →  {dst}")
            ok += 1
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  ✓  {name}/{src.name}")
            ok += 1
        except OSError as e:
            print(f"  ✗  {raw}: {e}", file=sys.stderr)
            fail += 1

    print(f"\n[done] {ok} copied, {skip} skipped, {fail} failed", file=sys.stderr)


if __name__ == "__main__":
    main()
