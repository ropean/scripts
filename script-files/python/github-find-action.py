#!/usr/bin/env python3
"""
@title github-find-action
@description Find workflow files that reference a specific GitHub Action.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

@example
    python github-find-action.py cloudflare/wrangler-action
    python github-find-action.py cloudflare/wrangler-action@v3
    python github-find-action.py cloudflare/wrangler-action "\\\\wsl.localhost\\Ubuntu\\home\\robot-u\\git"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PLATFORM_DEFAULTS = {
    "win32": r"D:\Git",
    "darwin": "~/Git",
    "linux": "~/Git",  # includes WSL
}

USES_RE = re.compile(
    r"^(?P<indent>\s*)(?:-\s*)?uses:\s*(?P<value>[^#\r\n]+?)(?:\s+#.*)?$",
    re.MULTILINE,
)


def default_git_dir() -> Path:
    raw = PLATFORM_DEFAULTS.get(sys.platform, "~/Git")
    return Path(raw).expanduser()


def normalize_package(value: str) -> str:
    cleaned = value.strip().strip("\"'")
    return cleaned.split("@", 1)[0].strip().casefold()


_SKIP_DIRS = {"node_modules", "__pycache__", "venv", ".venv"}

def iter_workflow_files(git_dir: Path) -> list[Path]:
    results: set[Path] = set()
    for root, dirs, files in os.walk(git_dir, followlinks=False):
        root_path = Path(root)
        if root_path.name == "workflows" and root_path.parent.name == ".github":
            results.update(
                root_path / f for f in files if f.endswith((".yml", ".yaml"))
            )
        # Prune: skip hidden dirs (except .github) and known large dirs
        dirs[:] = [
            d for d in dirs
            if d not in _SKIP_DIRS and (not d.startswith(".") or d == ".github")
        ]
    return sorted(results)

def find_package_references(git_dir: Path, package_name: str) -> list[dict]:
    matches: list[dict] = []
    normalized_target = normalize_package(package_name)

    for workflow_path in iter_workflow_files(git_dir):
        try:
            text = workflow_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"[warn] Cannot read {workflow_path}: {exc}", file=sys.stderr)
            continue

        workflow_matches: list[dict] = []
        for match in USES_RE.finditer(text):
            uses_value = match.group("value").strip().strip("\"'")
            if normalize_package(uses_value) != normalized_target:
                continue

            line_number = text.count("\n", 0, match.start()) + 1
            workflow_matches.append({"line": line_number, "uses": uses_value})

        if not workflow_matches:
            continue

        try:
            rel_path = workflow_path.relative_to(git_dir)
        except ValueError:
            rel_path = workflow_path

        matches.append(
            {
                "workflow": str(rel_path),
                "matches": workflow_matches,
            }
        )

    return matches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find workflows that reference a specific GitHub Action."
    )
    parser.add_argument(
        "pkg_name",
        help="GitHub Action name, e.g.: cloudflare/wrangler-action or cloudflare/wrangler-action@v3",
    )
    parser.add_argument(
        "git_dir",
        nargs="?",
        default=None,
        help=f"Root directory containing git repos (default: {default_git_dir()})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of a human-readable summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    git_dir = Path(args.git_dir).expanduser() if args.git_dir else default_git_dir()

    if not git_dir.is_dir():
        print(f"[error] Directory not found: {git_dir}", file=sys.stderr)
        sys.exit(1)

    matches = find_package_references(git_dir, args.pkg_name)
    result = {
        "git_dir": str(git_dir),
        "pkg_name": args.pkg_name,
        "workflow_count": len(matches),
        "matches": matches,
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print(f"git_dir: {git_dir}")
    print(f"pkg_name: {args.pkg_name}")
    print(f"workflow_count: {len(matches)}")

    for item in matches:
        print(f"\n{item['workflow']}")
        for hit in item["matches"]:
            print(f"  L{hit['line']}: {hit['uses']}")


if __name__ == "__main__":
    main()
