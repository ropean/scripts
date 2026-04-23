#!/usr/bin/env python3
"""
@title .NET Package Management
@description Unified entry point for .NET SDK setup, registry config, and package updates
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Provides an interactive menu to run individual tools or execute all steps
sequentially:
    1. Check / Install .NET SDK
    2. Check / Configure GitHub Package Registry
    3. Update NuGet Packages

Each step delegates to a dedicated script in the same directory.

@example
Usage example:
    python dotnet-package-manage.py

@requires dotnet-setup.py, dotnet-registry.py, dotnet-update-packages.py
"""

import os
import subprocess
import sys

# ── Constants ──────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    {
        "label": "Check / Install .NET SDK",
        "script": "dotnet-setup.py",
        "run_all_args": ["--install"],
    },
    {
        "label": "Check / Config GitHub Package Registry",
        "script": "dotnet-registry.py",
        "run_all_args": [],
    },
    {
        "label": "Update NuGet Packages",
        "script": "dotnet-update-packages.py",
        "run_all_args": [],
    },
]

# ── Colored output helpers ─────────────────────────────────────────────────────

_NO_COLOR = not sys.stdout.isatty()


def _colored(text: str, code: str) -> str:
    if _NO_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(text: str) -> str:
    return _colored(text, "32")


def yellow(text: str) -> str:
    return _colored(text, "33")


def red(text: str) -> str:
    return _colored(text, "31")


def cyan(text: str) -> str:
    return _colored(text, "36")


def dim(text: str) -> str:
    return _colored(text, "2")


# ── Execution ──────────────────────────────────────────────────────────────────


def run_step(step: dict, extra_args: list[str] | None = None) -> int:
    """Run a script and return its exit code."""
    script_path = os.path.join(SCRIPT_DIR, step["script"])
    cmd = [sys.executable, script_path] + (extra_args or [])
    print()
    print(cyan(f"{'─' * 60}"))
    print(cyan(f"  Step: {step['label']}"))
    print(cyan(f"  Script: {step['script']}"))
    print(cyan(f"{'─' * 60}"))
    result = subprocess.run(cmd)
    return result.returncode


def ask_continue() -> bool:
    """Ask user whether to continue after a failed step."""
    try:
        answer = input(yellow("  Continue to next step? (Y/n): ")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer != "n"


# ── Menu ───────────────────────────────────────────────────────────────────────


def show_menu() -> str | None:
    """Show interactive menu. Return '0'-'N' or None to exit."""
    print()
    print(f"  {green('[0]')} Run all steps (setup -> registry -> update)")
    for i, step in enumerate(STEPS):
        print(f"  {cyan(f'[{i + 1}]')} {step['label']}")
    print()

    max_idx = len(STEPS)
    while True:
        try:
            raw = input(f"  Enter your choice (0-{max_idx}, or X to exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw.upper() == "X":
            return None
        try:
            num = int(raw)
        except ValueError:
            print(red(f"  Invalid input. Enter 0-{max_idx}, or X."))
            continue
        if 0 <= num <= max_idx:
            return str(num)
        print(red(f"  Invalid input. Enter 0-{max_idx}, or X."))


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> int:
    print()
    print(cyan("=== .NET Package Management ==="))

    choice = show_menu()
    if choice is None:
        print(yellow("  Exiting."))
        return 0

    if choice == "0":
        for step in STEPS:
            rc = run_step(step, step["run_all_args"])
            if rc != 0:
                print()
                print(red(f"  Step '{step['label']}' exited with code {rc}."))
                if not ask_continue():
                    return rc
        print()
        print(green("All steps completed."))
        return 0

    idx = int(choice) - 1
    rc = run_step(STEPS[idx])
    return rc


if __name__ == "__main__":
    sys.exit(main())
