#!/usr/bin/env python3
"""
@title Git Config Guide
@description Interactive cross-platform Git configuration checker and setup wizard
@version 1.0.0
@see https://scripts.aceapp.dev

Checks and interactively updates global Git configuration across macOS, Linux,
and Windows (Git Bash / WSL). Covers identity, credential helpers, line endings,
encoding, performance, and useful aliases. Also prints ready-to-use project-level
.gitattributes content on demand.

@example
    python git-config-guide.py
    python git-config-guide.py --no-color
"""

import subprocess
import sys
import os
import platform
import shutil
import argparse

# ─────────────────────────────────────────────────────────────
# ANSI colors (auto-disabled on Windows cmd or when --no-color)
# ─────────────────────────────────────────────────────────────

def _supports_color(no_color: bool) -> bool:
    if no_color:
        return False
    if platform.system() == "Windows" and "WT_SESSION" not in os.environ:
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class C:
    """Terminal color helpers – patched to no-ops when color is off."""
    RESET = BOLD = DIM = GREEN = YELLOW = RED = CYAN = MAGENTA = BLUE = ""

    @classmethod
    def enable(cls):
        cls.RESET   = "\033[0m"
        cls.BOLD    = "\033[1m"
        cls.DIM     = "\033[2m"
        cls.GREEN   = "\033[32m"
        cls.YELLOW  = "\033[33m"
        cls.RED     = "\033[31m"
        cls.CYAN    = "\033[36m"
        cls.MAGENTA = "\033[35m"
        cls.BLUE    = "\033[34m"

    @classmethod
    def ok(cls, s):   return f"{cls.GREEN}{s}{cls.RESET}"
    @classmethod
    def warn(cls, s): return f"{cls.YELLOW}{s}{cls.RESET}"
    @classmethod
    def err(cls, s):  return f"{cls.RED}{s}{cls.RESET}"
    @classmethod
    def hi(cls, s):   return f"{cls.CYAN}{s}{cls.RESET}"
    @classmethod
    def b(cls, s):    return f"{cls.BOLD}{s}{cls.RESET}"
    @classmethod
    def dim(cls, s):  return f"{cls.DIM}{s}{cls.RESET}"


# ─────────────────────────────────────────────────────────────
# Git helpers
# ─────────────────────────────────────────────────────────────

def git_get(key: str) -> str:
    """Return current global git config value, or '' if not set."""
    try:
        result = subprocess.run(
            ["git", "config", "--global", key],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return ""


def git_set(key: str, value: str) -> bool:
    """Set a global git config key. Returns True on success."""
    result = subprocess.run(
        ["git", "config", "--global", key, value],
        capture_output=True, text=True
    )
    return result.returncode == 0


def git_available() -> bool:
    return shutil.which("git") is not None


# ─────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────

def section(title: str):
    width = 60
    print()
    print(C.b(C.BLUE + "─" * width + C.RESET))
    print(C.b(f"  {title}"))
    print(C.b(C.BLUE + "─" * width + C.RESET))


def prompt_update(key: str, current: str, recommended: str, hint: str = "") -> bool:
    """
    Show current value, suggest recommended, ask user whether to update.
    Returns True if a change was made.
    """
    label   = C.hi(key)
    cur_str = C.ok(current) if current else C.warn("(not set)")
    rec_str = C.b(recommended)

    print(f"\n  {label}")
    if hint:
        print(f"  {C.dim(hint)}")
    print(f"  Current   : {cur_str}")
    print(f"  Recommended: {rec_str}")

    if current == recommended:
        print(f"  {C.ok('✓ Already correct, skipping.')}")
        return False

    try:
        answer = input(f"  Set to {C.b(recommended)}? [Enter=skip / y=yes / custom value]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if answer.lower() == "y":
        value = recommended
    elif answer == "":
        print(f"  {C.dim('Skipped.')}")
        return False
    else:
        value = answer  # user typed a custom value

    if git_set(key, value):
        print(f"  {C.ok(f'✓ Set: {key} = {value}')}")
        return True
    else:
        print(f"  {C.err('✗ Failed to set value.')}")
        return False


def show_readonly(key: str, current: str, note: str = ""):
    """Just display a key's value without prompting."""
    cur_str = C.ok(current) if current else C.warn("(not set)")
    print(f"\n  {C.hi(key)}: {cur_str}")
    if note:
        print(f"  {C.dim(note)}")


# ─────────────────────────────────────────────────────────────
# Platform detection
# ─────────────────────────────────────────────────────────────

def detect_platform() -> str:
    """Returns 'macos', 'linux', 'wsl', or 'windows'."""
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    if system == "Linux":
        # Check for WSL
        try:
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    return "wsl"
        except OSError:
            pass
        return "linux"
    return "linux"


def recommended_autocrlf(plat: str) -> str:
    return "true" if plat == "windows" else "input"


def recommended_credential_helper(plat: str) -> str:
    if plat == "macos":
        return "osxkeychain"
    if plat == "windows":
        return "manager"
    # linux / wsl
    if shutil.which("git-credential-libsecret"):
        return "/usr/lib/git-core/git-credential-libsecret"
    return "cache --timeout=3600"


# ─────────────────────────────────────────────────────────────
# Check sections
# ─────────────────────────────────────────────────────────────

def check_identity():
    section("① Identity")
    for key in ("user.name", "user.email"):
        current = git_get(key)
        label   = C.hi(key)
        cur_str = C.ok(current) if current else C.err("(not set – REQUIRED)")
        print(f"\n  {label}: {cur_str}")
        if not current:
            try:
                val = input(f"  Enter value for {key}: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            if val:
                if git_set(key, val):
                    print(f"  {C.ok(f'✓ Set: {key} = {val}')}")
                else:
                    print(f"  {C.err('✗ Failed.')}")


def check_credential(plat: str):
    section("② Credential Helper")
    key     = "credential.helper"
    current = git_get(key)
    rec     = recommended_credential_helper(plat)

    hints = {
        "macos":   "macOS Keychain – secure system store, no plaintext.",
        "windows": "Git Credential Manager – comes bundled with Git for Windows.",
        "wsl":     "libsecret links into GNOME Keyring; fallback is memory cache.",
        "linux":   "memory cache (15 min–1 h) is safer than plaintext store.",
    }
    prompt_update(key, current, rec, hints.get(plat, ""))

    if plat in ("linux", "wsl") and current == "store":
        print(f"  {C.warn('⚠ store saves credentials in plaintext at ~/.git-credentials')}")
        print(f"  {C.dim('  Fine if your screen locks quickly (macOS-style). Keep it if intentional.')}")


def check_line_endings(plat: str):
    section("③ Line Endings (core.autocrlf)")
    hints = (
        "input  → commit LF as-is, never convert on checkout  (Linux/macOS/WSL)\n"
        "  true   → commit converts CRLF→LF, checkout converts LF→CRLF          (Windows)\n"
        "  false  → no conversion at all (not recommended for cross-platform work)"
    )
    prompt_update(
        "core.autocrlf",
        git_get("core.autocrlf"),
        recommended_autocrlf(plat),
        hints,
    )


def check_filemode(plat: str):
    section("④ File Permission Tracking (core.fileMode)")
    current = git_get("core.fileMode")
    if plat == "wsl":
        prompt_update(
            "core.fileMode", current, "false",
            "WSL mounts Windows drives with inconsistent permissions – set false globally."
        )
    else:
        show_readonly(
            "core.fileMode", current,
            "true = track +x changes (default, fine on native Linux/macOS)."
        )


def check_encoding():
    section("⑤ Encoding & Chinese Filename Support")

    items = [
        ("i18n.commitEncoding", "utf-8",  "Encoding for commit messages."),
        ("i18n.logOutputEncoding", "utf-8", "Encoding when displaying log output."),
        ("core.quotePath", "false",        "Show non-ASCII filenames (e.g. Chinese) unescaped in status/log."),
    ]
    for key, rec, hint in items:
        prompt_update(key, git_get(key), rec, hint)


def check_misc():
    section("⑥ Quality-of-Life Settings")

    items = [
        ("init.defaultBranch",  "main",      "Default branch name for new repos."),
        ("pull.rebase",         "false",      "false=merge, true=rebase on pull. Pick your team's convention."),
        ("push.default",        "current",    "Push only the current branch by default."),
        ("diff.algorithm",      "histogram",  "More accurate diff output than the default 'myers'."),
        ("rerere.enabled",      "true",       "Remember conflict resolutions and replay them automatically."),
        ("core.longPaths",      "true",       "Needed on Windows for deep directory trees."),
        ("color.ui",            "auto",       "Colorized output when printing to a terminal."),
    ]
    for key, rec, hint in items:
        prompt_update(key, git_get(key), rec, hint)


def check_editor():
    section("⑦ Default Editor")
    current = git_get("core.editor")
    choices = {
        "1": ("code --wait",  "VS Code"),
        "2": ("vim",          "Vim"),
        "3": ("nano",         "Nano"),
        "4": ("hx",           "Helix"),
    }
    cur_str = C.ok(current) if current else C.warn("(not set – git uses $EDITOR or vi)")
    print(f"\n  {C.hi('core.editor')}: {cur_str}")
    print(f"  Options: " + "  ".join(f"{k}={C.b(v[1])}" for k, v in choices.items()))
    try:
        ans = input("  Choose [1-4], type custom, or Enter to skip: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not ans:
        return
    value = choices[ans][0] if ans in choices else ans
    if git_set("core.editor", value):
        print(f"  {C.ok(f'✓ Set core.editor = {value}')}")


def check_aliases():
    section("⑧ Useful Aliases")
    aliases = [
        ("alias.st",      "status -sb",                        "Short, branch-aware status."),
        ("alias.lg",      "log --oneline --graph --decorate",   "Pretty one-line log graph."),
        ("alias.unstage", "reset HEAD --",                      "Unstage a file easily."),
        ("alias.last",    "log -1 HEAD",                        "Show last commit."),
        ("alias.aliases", "config --get-regexp alias",          "List all aliases."),
    ]
    for key, rec, hint in aliases:
        prompt_update(key, git_get(key), rec, hint)


# ─────────────────────────────────────────────────────────────
# Project-level output
# ─────────────────────────────────────────────────────────────

GITATTRIBUTES = """\
# ──────────────────────────────────────────
# .gitattributes – project-level line ending
# and binary file policy.
# Place this file in the repo root.
# ──────────────────────────────────────────

# Default: let Git decide (text=auto normalises to LF in repo)
* text=auto

# Explicit text files – always store as LF
*.js      text eol=lf
*.ts      text eol=lf
*.jsx     text eol=lf
*.tsx     text eol=lf
*.mjs     text eol=lf
*.cjs     text eol=lf
*.json    text eol=lf
*.jsonc   text eol=lf
*.md      text eol=lf
*.mdx     text eol=lf
*.html    text eol=lf
*.css     text eol=lf
*.scss    text eol=lf
*.less    text eol=lf
*.yaml    text eol=lf
*.yml     text eol=lf
*.toml    text eol=lf
*.ini     text eol=lf
*.cfg     text eol=lf
*.env     text eol=lf
*.sh      text eol=lf
*.bash    text eol=lf
*.zsh     text eol=lf
*.py      text eol=lf
*.rb      text eol=lf
*.go      text eol=lf
*.rs      text eol=lf
*.cs      text eol=lf
*.sql     text eol=lf
*.xml     text eol=lf
*.svg     text eol=lf
*.txt     text eol=lf
*.lock    text eol=lf -diff
Makefile  text eol=lf

# Windows-only scripts – keep CRLF on checkout
*.bat     text eol=crlf
*.cmd     text eol=crlf
*.ps1     text eol=crlf

# Binary – no conversion, no diff
*.png     binary
*.jpg     binary
*.jpeg    binary
*.gif     binary
*.webp    binary
*.ico     binary
*.pdf     binary
*.zip     binary
*.gz      binary
*.tar     binary
*.7z      binary
*.exe     binary
*.dll     binary
*.so      binary
*.dylib   binary
*.wasm    binary
*.ttf     binary
*.otf     binary
*.woff    binary
*.woff2   binary
*.eot     binary
*.mp4     binary
*.mp3     binary
*.wav     binary
*.ogg     binary
"""

GITIGNORE_ADDITIONS = """\
# ── OS ──────────────────────────────────
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
Thumbs.db
ehthumbs.db
Desktop.ini

# ── Editor ──────────────────────────────
.vscode/settings.json
.idea/
*.suo
*.user
*.swp
*~

# ── Secrets ─────────────────────────────
.env
.env.*
!.env.example
"""


def print_project_templates():
    section("⑨ Project-Level Templates")
    print(f"\n  {C.b('.gitattributes')}  {C.dim('(copy to your repo root)')}")
    print()
    for line in GITATTRIBUTES.splitlines():
        if line.startswith("#"):
            print("  " + C.dim(line))
        else:
            print("  " + line)

    print(f"\n  {C.b('Recommended additions for .gitignore')}")
    print()
    for line in GITIGNORE_ADDITIONS.splitlines():
        if line.startswith("#"):
            print("  " + C.dim(line))
        else:
            print("  " + line)


# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────

def print_summary():
    section("✅ Current Global Config")
    keys = [
        "user.name", "user.email",
        "credential.helper",
        "core.autocrlf", "core.fileMode", "core.quotePath", "core.editor", "core.longPaths",
        "i18n.commitEncoding", "i18n.logOutputEncoding",
        "init.defaultBranch", "pull.rebase", "push.default",
        "diff.algorithm", "rerere.enabled", "color.ui",
        "alias.st", "alias.lg", "alias.unstage", "alias.last",
    ]
    for key in keys:
        val = git_get(key)
        val_str = C.ok(val) if val else C.dim("(not set)")
        print(f"  {C.hi(key):<45} {val_str}")


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Interactive cross-platform Git configuration guide."
    )
    parser.add_argument("--no-color",    action="store_true", help="Disable colored output.")
    parser.add_argument("--summary-only",action="store_true", help="Just print current config, no prompts.")
    parser.add_argument("--templates",   action="store_true", help="Print project-level templates and exit.")
    args = parser.parse_args()

    if _supports_color(args.no_color):
        C.enable()

    if not git_available():
        print(C.err("✗ git not found in PATH. Please install Git first."))
        sys.exit(1)

    plat = detect_platform()
    plat_label = {"macos": "macOS", "linux": "Linux", "wsl": "WSL (Linux)", "windows": "Windows"}.get(plat, plat)

    print()
    print(C.b(C.MAGENTA + "╔══════════════════════════════════════════════╗" + C.RESET))
    print(C.b(C.MAGENTA + "║         git-config-guide  v1.0.0             ║" + C.RESET))
    print(C.b(C.MAGENTA + "╚══════════════════════════════════════════════╝" + C.RESET))
    print(f"\n  Platform detected: {C.b(plat_label)}")
    print(f"  Git version      : {C.dim(subprocess.getoutput('git --version'))}")
    print(f"\n  {C.dim('Press Enter to skip any item. Type a custom value to override the recommendation.')}")

    if args.templates:
        print_project_templates()
        return

    if args.summary_only:
        print_summary()
        return

    check_identity()
    check_credential(plat)
    check_line_endings(plat)
    check_filemode(plat)
    check_encoding()
    check_misc()
    check_editor()
    check_aliases()
    print_project_templates()
    print_summary()

    print()
    print(C.ok("  Done. Run `git config --global --list` to verify all settings."))
    print()


if __name__ == "__main__":
    main()
