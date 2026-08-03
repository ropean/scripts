#!/usr/bin/env python3
"""
@title github-fix-actions
@description Batch-fix GitHub Actions workflows across repos using resolved version targets.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Reads version targets from a JSON file (produced by github-fetch-versions.py)
and applies them to every workflow file found under the git root.

@example
    python github-fix-actions.py [git_dir] [-i FILE] [--dry-run] [-o REPORT]

Arguments:
    git_dir         Root directory containing your git repos (default: platform-dependent)
    -i / --input    Versions JSON file  (default: github-actions-versions.json in script dir)
    --dry-run       Preview changes without writing any files
    -o / --output   Save a Markdown report to this file
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).resolve().parent

# ════════════════════════════════════════════════════════════
#  USER CONFIG
# ════════════════════════════════════════════════════════════

DEFAULT_GIT_DIRS = {
    "win32":  r"D:\Git",
    "darwin": "~/Git",
    "linux":  "~/Git",  # includes WSL
}

# Top-level permissions to ensure exist in every workflow.
# Set to [] to disable this feature entirely.
REQUIRED_PERMISSIONS = [
    ("deployments", "write"),
    # ("contents", "read"),
]

# ════════════════════════════════════════════════════════════
#  END OF USER CONFIG
# ════════════════════════════════════════════════════════════

_SENSITIVE_KEY = re.compile(
    r"token|secret|password|passwd|pwd|api.?key|auth|credential|private.?key|cert",
    re.IGNORECASE,
)
_KV_LINE    = re.compile(r"^\s+(\w+)\s*:\s*(.+)$")
_EXPRESSION = re.compile(r"^\$\{\{")
_NON_SECRET = re.compile(r"^(true|false|yes|no|null|~|\d+|""|'')$", re.IGNORECASE)


# ── Terminal colors ───────────────────────────────────────

def _supports_color() -> bool:
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        return "WT_SESSION" in os.environ or bool(os.environ.get("TERM"))
    return True


if _supports_color():
    _C = {
        "green":  "\033[32m",
        "yellow": "\033[33m",
        "cyan":   "\033[36m",
        "red":    "\033[31m",
        "bold":   "\033[1m",
        "dim":    "\033[2m",
        "reset":  "\033[0m",
    }
else:
    _C = {k: "" for k in ("green", "yellow", "cyan", "red", "bold", "dim", "reset")}


def c(color: str, text: str) -> str:
    return f"{_C[color]}{text}{_C['reset']}"


# ── Path helpers ─────────────────────────────────────────

def resolve_git_dir(arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser()
    else:
        key = sys.platform if sys.platform in DEFAULT_GIT_DIRS else "linux"
        p = Path(DEFAULT_GIT_DIRS[key]).expanduser()
    # Skip resolve() for UNC paths (\\server\share) — it corrupts them on Windows
    if not str(p).startswith("\\\\"):
        p = p.resolve()
    if not p.is_dir():
        sys.exit(f"Error: directory not found: {p}")
    return p


def find_workflow_files(git_dir: Path):
    """Yield .yml/.yaml files under <git_dir>/*/.github/workflows/"""
    for repo in sorted(git_dir.iterdir()):
        if not repo.is_dir() or repo.name.startswith("."):
            continue
        wf_dir = repo / ".github" / "workflows"
        if not wf_dir.is_dir():
            continue
        for f in sorted(wf_dir.iterdir()):
            if f.suffix in (".yml", ".yaml"):
                yield f


# ── Version helpers ──────────────────────────────────────

def to_major_version(ver: str) -> str:
    """v6.0.2 → v6 | v3 → v3 | codeql-bundle-v2.25.1 → unchanged"""
    if not ver.startswith("v"):
        return ver
    return "v" + ver[1:].split(".")[0]


# ── Core transformations ─────────────────────────────────

def apply_package_upgrades(
    content: str, upgrades: list[tuple[str, str]]
) -> tuple[str, list[str]]:
    """Pin each action to its target version, regardless of current version."""
    changes: list[str] = []
    for action, target in upgrades:
        pattern = rf"({re.escape(action)}@)(\S+)"
        old_refs = set(re.findall(pattern, content))
        new_content, count = re.subn(pattern, lambda m, t=target: f"{m.group(1)}{t}", content)
        if count:
            for _, old_ver in old_refs:
                if old_ver != target:
                    changes.append(f"{action}@{old_ver}  →  @{target}")
            content = new_content
    return content, changes


def apply_permissions(content: str) -> tuple[str, list[str]]:
    """Ensure every key in REQUIRED_PERMISSIONS exists in the top-level permissions block."""
    if not REQUIRED_PERMISSIONS:
        return content, []

    lines = content.splitlines(keepends=True)
    changes: list[str] = []

    perm_start: int | None = None
    perm_end:   int | None = None
    jobs_line:  int | None = None

    for i, line in enumerate(lines):
        s = line.rstrip()
        if re.match(r"^permissions\s*:", s):
            perm_start = i
        if re.match(r"^jobs\s*:", s):
            jobs_line = i
        if (
            perm_start is not None
            and perm_end is None
            and i > perm_start
            and s
            and s[0] not in (" ", "\t", "#")
        ):
            perm_end = i

    if perm_start is not None and perm_end is None:
        perm_end = len(lines)

    # Skip scalar form: "permissions: read-all"
    if perm_start is not None:
        scalar = re.match(r"^permissions\s*:\s*(\S+)", lines[perm_start].rstrip())
        if scalar and scalar.group(1) not in ("", "{}"):
            return content, []

    if perm_start is None:
        if jobs_line is None:
            return content, []
        block = ["permissions:\n"]
        for key, val in REQUIRED_PERMISSIONS:
            block.append(f"  {key}: {val}\n")
        block.append("\n")
        lines = lines[:jobs_line] + block + lines[jobs_line:]
        desc = ", ".join(f"{k}: {v}" for k, v in REQUIRED_PERMISSIONS)
        changes.append(f"added permissions block  ({desc})")
    else:
        existing: set[str] = set()
        for i in range(perm_start + 1, perm_end):  # type: ignore[arg-type]
            m = re.match(r"^  ([\w-]+)\s*:", lines[i])
            if m:
                existing.add(m.group(1))

        missing = [(k, v) for k, v in REQUIRED_PERMISSIONS if k not in existing]
        if not missing:
            return content, []

        insert_at = perm_start + 1
        for i in range(perm_start + 1, perm_end):  # type: ignore[arg-type]
            if lines[i].strip():
                insert_at = i + 1

        for key, val in reversed(missing):
            lines.insert(insert_at, f"  {key}: {val}\n")

        for key, val in missing:
            changes.append(f"added permission: {key}: {val}")

    return "".join(lines), changes


# ── Secrets check ────────────────────────────────────────

def check_hardcoded_secrets(content: str) -> list[str]:
    """Return 'line N: KEY' for indented key-value pairs that look like hardcoded secrets."""
    findings = []
    for lineno, line in enumerate(content.splitlines(), 1):
        m = _KV_LINE.match(line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if not _SENSITIVE_KEY.search(key):
            continue
        val = raw.strip('"').strip("'")
        if _EXPRESSION.match(val) or _EXPRESSION.match(raw):
            continue
        if _NON_SECRET.match(val):
            continue
        if len(val) <= 8:
            continue
        findings.append(f"line {lineno}: {key}")
    return findings


# ── File processor ────────────────────────────────────────

def process_file(
    path: Path, upgrades: list[tuple[str, str]], dry_run: bool = False
) -> dict:
    original = path.read_text(encoding="utf-8")
    content  = original

    content, pkg_changes  = apply_package_upgrades(content, upgrades)
    content, perm_changes = apply_permissions(content)
    sec_warnings          = check_hardcoded_secrets(original)

    modified = content != original
    if modified and not dry_run:
        path.write_text(content, encoding="utf-8")

    return {
        "path":         path,
        "pkg_changes":  pkg_changes,
        "perm_changes": perm_changes,
        "sec_warnings": sec_warnings,
        "modified":     modified,
    }


# ── Report ────────────────────────────────────────────────

def save_report(results: list[dict], git_dir: Path, dry_run: bool, out: Path) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    modified = [r for r in results if r["modified"]]
    skipped  = [r for r in results if not r["modified"]]

    md: list[str] = [
        "# GitHub Actions Fix Report",
        "",
        f"- **Date**: {ts}",
        f"- **Git dir**: `{git_dir}`",
        f"- **Mode**: {'dry-run (no files written)' if dry_run else 'applied'}",
        f"- **Total**: {len(results)} files scanned, "
        f"{len(modified)} modified, {len(skipped)} skipped",
        "",
        f"## Modified ({len(modified)} files)", "",
    ]
    for r in modified:
        rel = r["path"].relative_to(git_dir)
        md.append(f"### `{rel}`")
        if r["pkg_changes"]:
            md.append("**Package upgrades:**")
            for ch in r["pkg_changes"]:
                md.append(f"- {ch.strip()}")
        if r["perm_changes"]:
            md.append("**Permissions:**")
            for ch in r["perm_changes"]:
                md.append(f"- {ch.strip()}")
        md.append("")

    md += [f"## Skipped / already up to date ({len(skipped)} files)", ""]
    for r in skipped:
        md.append(f"- `{r['path'].relative_to(git_dir)}`")
    md.append("")

    warned = [r for r in results if r["sec_warnings"]]
    md += [f"## Potential hardcoded secrets ({len(warned)} files)", ""]
    if warned:
        for r in warned:
            rel = r["path"].relative_to(git_dir)
            for w in r["sec_warnings"]:
                md.append(f"- `{rel}` — {w}")
    else:
        md.append("None detected.")
    md.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md), encoding="utf-8")
    print(c("green", f"Report saved → {out}"))


# ── Entry point ───────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-fix GitHub Actions workflows across repos."
    )
    parser.add_argument(
        "git_dir", nargs="?",
        help="Root directory of your git repos (default: platform-specific)",
    )
    parser.add_argument(
        "-i", "--input",
        default=str(SCRIPTS_DIR / "github-actions-versions.json"),
        metavar="FILE",
        help="Versions JSON file (default: github-actions-versions.json in script dir)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing any files",
    )
    parser.add_argument(
        "--exact", action="store_true", default=False,
        help="Pin to the exact version (e.g. v6.0.2); default uses major only (e.g. v6). "
             "Only affects versions starting with 'v'.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        metavar="FILE",
        help="Save a Markdown report to this file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # ── Load versions ─────────────────────────────────────
    versions_path = Path(args.input)
    if not versions_path.exists():
        print(f"[error] Versions file not found: {versions_path}", file=sys.stderr)
        print(
            "  Run: python github-fetch-versions.py",
            file=sys.stderr,
        )
        sys.exit(1)

    versions: dict[str, str] = json.loads(versions_path.read_text(encoding="utf-8"))
    if args.exact:
        upgrades: list[tuple[str, str]] = list(versions.items())
    else:
        upgrades = [(action, to_major_version(ver)) for action, ver in versions.items()]
    print(f"[info] Loaded {len(upgrades)} version targets from {versions_path.name} "
          f"({'exact' if args.exact else 'major only'})",
          file=sys.stderr)

    # ── Setup ─────────────────────────────────────────────
    git_dir = resolve_git_dir(args.git_dir)
    dry_run = args.dry_run

    label = c("yellow", " [DRY RUN]") if dry_run else ""
    print(c("bold", f"\ngithub-fix-actions{label}"))
    print(f"Scanning: {c('cyan', str(git_dir))}\n")

    files = list(find_workflow_files(git_dir))
    if not files:
        sys.exit("No workflow files found.")

    # ── Process ───────────────────────────────────────────
    results: list[dict] = []
    for f in files:
        r = process_file(f, upgrades, dry_run=dry_run)
        results.append(r)
        rel = f.relative_to(git_dir)
        if r["modified"]:
            print(c("green", f"  ✓  {rel}"))
            for ch in r["pkg_changes"] + r["perm_changes"]:
                print(c("dim", f"       {ch.strip()}"))
        else:
            print(c("dim", f"  –  {rel}"))
        if dry_run:
            for w in r["sec_warnings"]:
                print(c("yellow", f"  ⚠  {rel}  ({w})"))

    # ── Summary ───────────────────────────────────────────
    modified = [r for r in results if r["modified"]]
    print(f"\n{'─' * 52}")
    print(f"  Scanned:  {len(results)} files")
    print(c("green",  f"  Modified: {len(modified)} files"))
    print(c("dim",    f"  Skipped:  {len(results) - len(modified)} files"))
    if dry_run:
        warned = [r for r in results if r["sec_warnings"]]
        if warned:
            total = sum(len(r["sec_warnings"]) for r in warned)
            print(c("yellow", f"  Secrets: {total} potential hardcoded value(s) in {len(warned)} file(s)"))
        print(c("yellow", "\n  [DRY RUN] No files were written."))

    if args.output:
        save_report(results, git_dir, dry_run, Path(args.output))


if __name__ == "__main__":
    main()
