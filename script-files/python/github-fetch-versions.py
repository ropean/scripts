#!/usr/bin/env python3
"""
@title github-fetch-versions
@description Fetch the latest major version for each GitHub Action via the GitHub API.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Reads a JSON list of action refs (e.g. from github-scan-actions.py --list),
queries the GitHub API concurrently, and writes a name→version JSON map.

@example
    python github-fetch-versions.py [-i FILE] [-o FILE] [--threads N]

Arguments:
    -i / --input    Input JSON file  (default: github-scan-actions.json in script dir)
    -o / --output   Output JSON file (default: github-actions-versions.json in script dir)
    --threads N     Concurrent API requests (default: 8)

@requires GITHUB_TOKEN environment variable (optional, raises rate limit)
"""

import json
import os
import re
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import request as urllib_request, error as urllib_error

SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT  = SCRIPTS_DIR / "github-scan-actions.json"
DEFAULT_OUTPUT = SCRIPTS_DIR / "github-actions-versions.json"
API_BASE       = "https://api.github.com"


# ════════════════════════════════════════════════════════════
# Filtering
# ════════════════════════════════════════════════════════════

def should_skip(ref: str) -> bool:
    """Skip local actions and reusable workflow references."""
    if ref.startswith("./"):
        return True
    if "/.github/workflows/" in ref:
        return True
    return False


def base_name(ref: str) -> str:
    """Strip @version suffix and sub-path → owner/repo.

    "github/codeql-action/init@v3"  → "github/codeql-action"
    "actions/checkout@v4"           → "actions/checkout"
    """
    path = ref.split("@")[0]
    parts = path.split("/")
    return "/".join(parts[:2])


# ════════════════════════════════════════════════════════════
# Version extraction
# ════════════════════════════════════════════════════════════

def normalize_version(tag: str) -> str:
    """
    "v4.3.5"  → "v4.3.5"
    "4.3.5"   → "v4.3.5"
    "v4"      → "v4"
    "stable"  → "stable"   (non-semver kept as-is)
    """
    m = re.match(r"^v?(\d+.*)$", tag)
    if m:
        return f"v{m.group(1)}"
    return tag


# ════════════════════════════════════════════════════════════
# GitHub API
# ════════════════════════════════════════════════════════════

def build_headers(token: str | None) -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-fetch-versions",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get_json(url: str, headers: dict) -> tuple[object, str | None]:
    """Fetch URL → (parsed_json, error_str). Returns (None, err) on failure."""
    try:
        req = urllib_request.Request(url, headers=headers)
        with urllib_request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()), None
    except urllib_error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)


def fetch_latest_version(
    owner_repo: str, headers: dict
) -> tuple[str, str | None, str | None]:
    """Returns (owner_repo, version_or_None, error_or_None)."""
    owner, repo = owner_repo.split("/", 1)

    # 1. Try /releases/latest
    data, err = _get_json(f"{API_BASE}/repos/{owner}/{repo}/releases/latest", headers)
    if data is not None:
        tag = data.get("tag_name", "")  # type: ignore[union-attr]
        if tag:
            return owner_repo, normalize_version(tag), None

    # 2. Fallback: /tags (first result is most recent)
    if err and not err.startswith("HTTP 404"):
        return owner_repo, None, err

    data, err = _get_json(f"{API_BASE}/repos/{owner}/{repo}/tags", headers)
    if data and isinstance(data, list) and data:
        tag = data[0].get("name", "")
        if tag:
            return owner_repo, normalize_version(tag), None

    return owner_repo, None, err or "no releases or tags found"


# ════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch latest major versions for GitHub Actions from the GitHub API."
    )
    p.add_argument(
        "-i", "--input",
        default=str(DEFAULT_INPUT),
        metavar="FILE",
        help=f"Input JSON list of action refs (default: {DEFAULT_INPUT.name})",
    )
    p.add_argument(
        "-o", "--output",
        default=str(DEFAULT_OUTPUT),
        metavar="FILE",
        help=f"Output JSON name→version map (default: {DEFAULT_OUTPUT.name})",
    )
    p.add_argument(
        "--threads",
        type=int,
        default=8,
        metavar="N",
        help="Number of concurrent API requests (default: 8)",
    )
    return p.parse_args()


def check_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        print("[auth] Using GITHUB_TOKEN from environment.", file=sys.stderr)
        return token

    print(
        "[warn] GITHUB_TOKEN not set. Unauthenticated requests are limited to "
        "60/hour and may fail on large lists.",
        file=sys.stderr,
    )
    try:
        ans = input("Continue without token? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = ""

    if ans in ("n", "no"):
        print("Aborted.", file=sys.stderr)
        sys.exit(0)
    return None


def main() -> None:
    args = parse_args()

    # ── Load input ───────────────────────────────────────────
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[error] Input file not found: {in_path}", file=sys.stderr)
        print(
            "  Run: python github-scan-actions.py --list -o github-scan-actions.json",
            file=sys.stderr,
        )
        sys.exit(1)

    refs: list[str] = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(refs, list):
        print("[error] Input file must be a JSON array.", file=sys.stderr)
        sys.exit(1)

    # ── Deduplicate base names, skipping irrelevant refs ─────
    names: list[str] = sorted(
        {base_name(r) for r in refs if not should_skip(r)}
    )
    skipped = [r for r in refs if should_skip(r)]

    print(f"[info] {len(refs)} refs → {len(names)} unique actions "
          f"({len(skipped)} skipped).", file=sys.stderr)
    if skipped:
        for s in skipped:
            print(f"  skip: {s}", file=sys.stderr)

    # ── Auth ─────────────────────────────────────────────────
    token = check_token()
    headers = build_headers(token)

    # ── Fetch concurrently ───────────────────────────────────
    results: dict[str, str] = {}
    errors:  dict[str, str] = {}

    print(f"Fetching {len(names)} actions with {args.threads} threads …", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {pool.submit(fetch_latest_version, n, headers): n for n in names}
        for fut in as_completed(futures):
            name, version, err = fut.result()
            if version:
                results[name] = version
                print(f"  ✓  {name:<50} {version}", file=sys.stderr)
            else:
                errors[name] = err or "unknown error"
                print(f"  ✗  {name:<50} {err}", file=sys.stderr)

    if errors:
        print(f"\n[warn] {len(errors)} action(s) could not be resolved:", file=sys.stderr)
        for name, err in errors.items():
            print(f"  {name}: {err}", file=sys.stderr)

    # ── Write output ─────────────────────────────────────────
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(dict(sorted(results.items())), indent=2, ensure_ascii=False)
    out_path.write_text(json_text, encoding="utf-8")
    print(f"\n[saved] {out_path}  ({len(results)} entries)", file=sys.stderr)
    print(json_text)


if __name__ == "__main__":
    main()
