#!/usr/bin/env python3
"""
@title push-secrets
@description Push secrets from a .dev.vars file to a Cloudflare Pages project via wrangler.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Reads KEY=VALUE pairs from a .dev.vars (or any env-style) file and pushes
them as Cloudflare Pages secrets using `wrangler pages secret put`.

Secrets are discovered automatically from the file — no hard-coded list.

Supports Windows, macOS, Linux, and WSL paths for DEV_VARS_PATH.

@example
    # Full args:
    python push-secrets.py --vars-path C:/project/.dev.vars --project my-app

    # Interactive prompts (no args):
    python push-secrets.py

@requires wrangler (in PATH)
@see md-files/help/script-template.md
"""

import argparse
import subprocess
import sys
from pathlib import Path

# resolve_path lives next to this file
sys.path.insert(0, str(Path(__file__).parent))
from path_utils import resolve_path  # noqa: E402  (local import after sys.path tweak)

# ════════════════════════════════════════════════════════════
#  COLORS
# ════════════════════════════════════════════════════════════

def _supports_color() -> bool:
    return sys.stdout.isatty() and sys.platform != "win32" or (
        sys.platform == "win32" and "ANSICON" in __import__("os").environ
    )


def _c(code: int, text: str) -> str:
    if not _supports_color():
        return text
    return f"\033[{code}m{text}\033[0m"


INFO  = lambda t: print(_c(36, t))
OK    = lambda t: print(_c(32, t))
WARN  = lambda t: print(_c(33, f"WARN:  {t}"), file=sys.stderr)
ERR   = lambda t: print(_c(31, f"ERROR: {t}"), file=sys.stderr)

# ════════════════════════════════════════════════════════════
#  PARSING
# ════════════════════════════════════════════════════════════

def parse_env_file(path: Path) -> dict[str, str]:
    """Return KEY→value pairs from an env-style file, skipping blanks/comments."""
    vars_: dict[str, str] = {}
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip()
            # Strip surrounding quotes if present
            if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            if key:
                vars_[key] = value
    return vars_


# ════════════════════════════════════════════════════════════
#  PUSH
# ════════════════════════════════════════════════════════════

def push_secrets(vars_path: Path, project: str) -> None:
    INFO(f"\nReading vars from: {vars_path}")

    if not vars_path.exists():
        ERR(f"{vars_path} not found.")
        ERR("Create it from the example:  cp .dev.vars.example .dev.vars")
        sys.exit(1)

    secrets = parse_env_file(vars_path)
    if not secrets:
        ERR("No KEY=VALUE pairs found in the file.")
        sys.exit(1)

    INFO(f"Found {len(secrets)} secret(s): {', '.join(secrets)}")
    INFO(f"Target project: {project}\n")

    # On Windows, npm-installed CLIs are .cmd shims that require shell=True to resolve.
    use_shell = sys.platform == "win32"

    pushed = 0
    for key, value in secrets.items():
        try:
            result = subprocess.run(
                ["wrangler", "pages", "secret", "put", key, "--project-name", project],
                input=value,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                shell=use_shell,
            )
            if result.returncode == 0:
                OK(f"  + {key}")
                pushed += 1
            else:
                WARN(f"wrangler exited {result.returncode} for {key}: {result.stderr.strip()}")
        except FileNotFoundError:
            ERR("wrangler not found. Install it:  npm install -g wrangler")
            sys.exit(1)

    print()
    OK(f"Done - {pushed}/{len(secrets)} secret(s) pushed to project '{project}'.")


# ════════════════════════════════════════════════════════════
#  INTERACTIVE PROMPT
# ════════════════════════════════════════════════════════════

def _prompt(label: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    try:
        value = input(f"  {label}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return value or default


def gather_args_interactively() -> tuple[Path, str]:
    print(_c(36, "\n── push-secrets interactive mode ──\n"))
    raw_path = _prompt("Path to .dev.vars file (supports Windows/WSL/Unix paths)")
    while not raw_path:
        WARN("DEV_VARS_PATH is required.")
        raw_path = _prompt("Path to .dev.vars file")

    project = _prompt("Cloudflare Pages project name")
    while not project:
        WARN("PROJECT is required.")
        project = _prompt("Cloudflare Pages project name")

    return resolve_path(raw_path), project


# ════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push .dev.vars secrets to a Cloudflare Pages project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python push-secrets.py --vars-path C:/proj/.dev.vars --project my-app\n"
            "  python push-secrets.py --vars-path /mnt/c/proj/.dev.vars --project my-app\n"
            "  python push-secrets.py                    # interactive prompts\n"
        ),
    )
    parser.add_argument(
        "--vars-path", "-v",
        metavar="DEV_VARS_PATH",
        help="Path to the .dev.vars (or any KEY=VALUE) file. "
             "Accepts Windows (C:\\…), WSL (/mnt/c/…), macOS/Linux paths.",
    )
    parser.add_argument(
        "--project", "-p",
        metavar="PROJECT",
        help="Cloudflare Pages project name.",
    )
    args = parser.parse_args()

    if args.vars_path and args.project:
        vars_path = resolve_path(args.vars_path)
        project   = args.project
    elif args.vars_path or args.project:
        # Partial args — fill missing ones interactively
        if not args.vars_path:
            WARN("--vars-path is required.")
            raw = _prompt("Path to .dev.vars file")
            vars_path = resolve_path(raw)
        else:
            vars_path = resolve_path(args.vars_path)

        if not args.project:
            WARN("--project is required.")
            project = _prompt("Cloudflare Pages project name")
        else:
            project = args.project
    else:
        vars_path, project = gather_args_interactively()

    push_secrets(vars_path, project)


if __name__ == "__main__":
    main()
