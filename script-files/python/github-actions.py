#!/usr/bin/env python3
"""
@title github-actions
@description Interactive menu for the GitHub Actions toolchain (scan, fetch versions, preview, apply).
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

  1  Scan repos        -> github-scan-actions.json
  2  Fetch versions    -> github-actions-versions.json
  3  Preview updates   (dry-run, no writes)
  4  Apply updates     (writes workflow files)
  --
  0  Run all: 1 -> 2 -> 3 -> confirm -> 4

@example
    python github-actions.py [git_dir]
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

SCAN_JSON = SCRIPTS_DIR / "github-scan-actions.json"
VERSIONS_JSON = SCRIPTS_DIR / "github-actions-versions.json"

SCAN_SCRIPT = SCRIPTS_DIR / "github-scan-actions.py"
FETCH_SCRIPT = SCRIPTS_DIR / "github-fetch-versions.py"
FIX_SCRIPT = SCRIPTS_DIR / "github-fix-actions.py"


def _supports_color() -> bool:
    if os.name == "nt":
        return "WT_SESSION" in os.environ or bool(os.environ.get("TERM"))
    return sys.stdout.isatty()


if _supports_color():
    _C = {
        "green": "\033[32m",
        "yellow": "\033[33m",
        "cyan": "\033[36m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }
else:
    _C = {k: "" for k in ("green", "yellow", "cyan", "bold", "dim", "reset")}


def c(color: str, text: str) -> str:
    return f"{_C[color]}{text}{_C['reset']}"


def run(cmd: list[str]) -> int:
    """Run a command, streaming output. Returns exit code."""
    print(c("dim", f"\n> {' '.join(str(x) for x in cmd)}\n"))
    result = subprocess.run(cmd)
    return result.returncode


def ask_git_dir(default: str) -> str:
    """Prompt for git root; return default on empty input."""
    try:
        val = input(f"Git root [{default}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        val = ""
    return val if val else default


def confirm(prompt: str = "Proceed?") -> bool:
    try:
        ans = input(f"{prompt} [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = ""
    return ans not in ("n", "no")


def ask_version_mode(default_exact: bool = False) -> bool:
    """Prompt for version pinning mode. Returns True for exact mode."""
    default_choice = "2" if default_exact else "1"
    try:
        print("Version mode:")
        print(f"  1  major  {'(default)' if not default_exact else ''}".rstrip())
        print(f"  2  exact  {'(default)' if default_exact else ''}".rstrip())
        ans = input(f"Choose [1-2] ({default_choice}): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = ""

    if not ans:
        return default_exact
    if ans in ("1", "m", "major", "major-only"):
        return False
    if ans in ("2", "e", "exact", "full"):
        return True

    fallback = "exact" if default_exact else "major"
    print(c("yellow", f"  Invalid mode: {ans!r}; using {fallback}."))
    return default_exact


def default_git_dir() -> str:
    defaults = {
        "win32": r"D:\Git",
        "darwin": "~/Git",
        "linux": "~/Git",
    }
    return defaults.get(sys.platform, "~/Git")


def file_status(path: Path) -> str:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            count = len(data) if isinstance(data, (list, dict)) else "?"
            ts = datetime.fromtimestamp(path.stat().st_mtime).strftime("%m-%d %H:%M")
            return c("green", f"{count} entries  [{ts}]")
        except Exception:
            return c("yellow", "exists")
    return c("dim", "not found")


def print_menu(git_dir: str) -> None:
    print()
    print(c("bold", "  GitHub Actions 工具集"))
    print(f"  {'-' * 54}")
    print(f"  git root : {c('cyan', git_dir)}")
    print(f"  scan     : {file_status(SCAN_JSON)}")
    print(f"  versions : {file_status(VERSIONS_JSON)}")
    print(f"  {'-' * 54}")
    print(f"  {c('bold', '1')}  扫描仓库，提取 action 清单    github-scan-actions.json")
    print(f"  {c('bold', '2')}  查询 GitHub 最新版本          github-actions-versions.json")
    print(f"  {c('bold', '3')}  预览更新  {c('yellow', '(dry-run，不写文件)')}")
    print(f"  {c('bold', '4')}  执行更新  {c('green', '(写入 workflow 文件)')}")
    print(f"  {'-' * 54}")
    print(f"  {c('bold', '0')}  串联执行  1  2  预览  确认  写入")
    print(f"  {c('bold', 'q')}  退出")
    print(f"  {'-' * 54}")


def do_scan(git_dir: str) -> int:
    return run([PYTHON, str(SCAN_SCRIPT), "--list", "-o", str(SCAN_JSON), git_dir])


def do_fetch() -> int:
    return run([PYTHON, str(FETCH_SCRIPT), "-i", str(SCAN_JSON), "-o", str(VERSIONS_JSON)])


def do_fix(git_dir: str, dry_run: bool, exact: bool = True) -> int:
    cmd = [PYTHON, str(FIX_SCRIPT), "-i", str(VERSIONS_JSON), git_dir]
    if exact:
        cmd.append("--exact")
    if dry_run:
        cmd.append("--dry-run")
    return run(cmd)


def do_all(git_dir: str) -> None:
    exact = ask_version_mode(default_exact=False)
    mode_label = "exact" if exact else "major"

    print(c("bold", "\n  串联执行"))
    print(c("dim", f"  version mode: {mode_label}"))

    rc = do_scan(git_dir)
    if rc != 0:
        print(c("yellow", "\n[!] 扫描失败，中止。"))
        return

    rc = do_fetch()
    if rc != 0:
        print(c("yellow", "\n[!] 版本查询失败，中止。"))
        return

    print(c("bold", "\n  预览 (dry-run)"))
    do_fix(git_dir, dry_run=True, exact=exact)

    print()
    if not confirm("确认写入所有变更?"):
        print("已取消。")
        return

    do_fix(git_dir, dry_run=False, exact=exact)


def main() -> None:
    git_dir = sys.argv[1] if len(sys.argv) > 1 else default_git_dir()

    print_menu(git_dir)
    try:
        choice = input("  选择 [0-4 / q]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n再见。")
        return

    if choice == "q":
        print("再见。")
    elif choice == "1":
        git_dir = ask_git_dir(git_dir)
        do_scan(git_dir)
    elif choice == "2":
        do_fetch()
    elif choice == "3":
        git_dir = ask_git_dir(git_dir)
        exact = ask_version_mode(default_exact=False)
        do_fix(git_dir, dry_run=True, exact=exact)
    elif choice == "4":
        git_dir = ask_git_dir(git_dir)
        exact = ask_version_mode(default_exact=False)
        if confirm(f"将写入 {git_dir} 下所有 workflow 文件，确认?"):
            do_fix(git_dir, dry_run=False, exact=exact)
        else:
            print("已取消。")
    elif choice == "0":
        git_dir = ask_git_dir(git_dir)
        do_all(git_dir)
    else:
        print(c("yellow", "  无效选项。"))


if __name__ == "__main__":
    main()
