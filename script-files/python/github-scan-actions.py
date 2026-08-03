#!/usr/bin/env python3
"""
@title github-scan-actions
@description Scan GitHub Actions workflows across repos and summarize `uses:` references.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

@example
    python github-scan-actions.py [git_dir] [-o FILE] [-l]

Arguments:
    git_dir         Root directory containing your git repos (default: platform-dependent)
    -o / --output   Save JSON result to this file
    -l / --list     Output a flat sorted list of unique action names only (no counts/repos)
"""

import json
import re
import sys
import argparse
from collections import defaultdict
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

# ════════════════════════════════════════════════════════════
# Platform defaults
# ════════════════════════════════════════════════════════════

PLATFORM_DEFAULTS = {
    "win32":  r"D:\Git",
    "darwin": "~/Git",
    "linux":  "~/Git",  # includes WSL
}


def default_git_dir() -> Path:
    raw = PLATFORM_DEFAULTS.get(sys.platform, "~/Git")
    return Path(raw).expanduser()


# ════════════════════════════════════════════════════════════
# Core logic
# ════════════════════════════════════════════════════════════

USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s+(.+)$", re.MULTILINE)


def scan_workflows(git_dir: Path) -> dict:
    """
    Scan all .github/workflows/*.yml and *.yaml files under git_dir.

    Returns a dict shaped like:
    {
      "action@version": {"count": int, "repos": ["repo/workflow.yml", ...]},
      ...
    }
    """
    summary: dict[str, dict] = defaultdict(lambda: {"count": 0, "repos": []})
    workflow_files = sorted({
        *git_dir.glob("*/.github/workflows/*.yml"),
        *git_dir.glob("*/.github/workflows/*.yaml"),
    })

    if not workflow_files:
        print(f"[warn] No workflow files found under: {git_dir}", file=sys.stderr)
        return {}

    for wf_path in workflow_files:
        try:
            label = str(wf_path.relative_to(git_dir))
        except ValueError:
            label = str(wf_path)

        try:
            text = wf_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"[warn] Cannot read {wf_path}: {e}", file=sys.stderr)
            continue

        for match in USES_RE.finditer(text):
            action = match.group(1).strip().split("#")[0].strip()
            if not action:
                continue
            summary[action]["count"] += 1
            summary[action]["repos"].append(label)

    return dict(sorted(summary.items()))


def build_report(git_dir: Path, summary: dict) -> dict:
    from datetime import datetime, timezone
    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "git_dir": str(git_dir),
        "total_unique_actions": len(summary),
        "total_uses": sum(v["count"] for v in summary.values()),
        "actions": summary,
    }


# ════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan GitHub Actions `uses:` across all repos in a directory."
    )
    parser.add_argument(
        "git_dir",
        nargs="?",
        default=None,
        help=f"Root directory of your git repos (default: {default_git_dir()})",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        default=None,
        help=f"Save JSON output to this file (default when omitted: print to stdout only)",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Output a flat sorted list of unique action names only (no counts/repos)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    git_dir = Path(args.git_dir).expanduser() if args.git_dir else default_git_dir()
    if not git_dir.is_dir():
        print(f"[error] Directory not found: {git_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {git_dir} …", file=sys.stderr)

    summary = scan_workflows(git_dir)

    if args.list:
        json_text = json.dumps(sorted(summary.keys()), indent=2, ensure_ascii=False)
        print(f"[info] {len(summary)} unique actions.", file=sys.stderr)
    else:
        report = build_report(git_dir, summary)
        json_text = json.dumps(report, indent=2, ensure_ascii=False)
        workflow_count = len({r for v in summary.values() for r in v["repos"]})
        print(
            f"[info] {report['total_unique_actions']} unique actions, "
            f"{report['total_uses']} total uses across {workflow_count} workflow files.",
            file=sys.stderr,
        )

    print(json_text)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json_text, encoding="utf-8")
        print(f"[saved] {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
