#!/usr/bin/env python3
"""
@title github-build-workflow
@description Interactive GitHub Actions workflow generator with action versions auto-pinned.
@author ropean, Claude Sonnet (Anthropic)
@version 1.0.0

Generates .github/workflows/*.yml from templates, with action versions
automatically pinned from github-actions-versions.json.

@example
    python scripts/github-build-workflow.py [-o DIR] [-v FILE]

Options:
    -o / --output    Output directory (default: .github/workflows/)
    -v / --versions  Versions JSON   (default: scripts/github-actions-versions.json)
"""

import json
import re
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR      = Path(__file__).resolve().parent
DEFAULT_VERSIONS = SCRIPTS_DIR / "github-actions-versions.json"

# ── GitHub expression shorthands (avoids {{ }} escaping in f-strings) ─────────

G = {
    "ref":          "${{ github.ref }}",
    "workflow":     "${{ github.workflow }}",
    "sha":          "${{ github.sha }}",
    "repo":         "${{ github.repository }}",
    "actor":        "${{ github.actor }}",
    "token":        "${{ secrets.GITHUB_TOKEN }}",
    "tag":          "${{ github.ref_name }}",
    "ref_name":     "${{ github.ref_name }}",
    "event_name":   "${{ github.event_name }}",
    "pr_ref":       "${{ github.event.pull_request.number || github.ref }}",
    "matrix_node":  "${{ matrix.node }}",
    "meta_tags":    "${{ steps.meta.outputs.tags }}",
    "meta_labels":  "${{ steps.meta.outputs.labels }}",
    "inputs_env":    "${{ inputs.environment }}",
    # Reusable expression: push → derive from branch, dispatch → use input
    "deploy_env":    "${{ github.event_name == 'push' && (startsWith(github.ref_name, 'dev') && 'dev' || 'release') || inputs.environment }}",
    # Job-level env var (avoids repeating the expression in steps)
    "gh_env":        "${{ env.GH_ENV }}",
    "step_cf_project": "${{ steps.cf.outputs.project }}",
    "step_cf_domain":  "${{ steps.cf.outputs.domain }}",
}

# ── Version fallbacks ──────────────────────────────────────────────────────────

FALLBACKS: dict[str, str] = {
    "actions/checkout":             "v4",
    "actions/setup-node":           "v4",
    "actions/upload-artifact":      "v4",
    "actions/download-artifact":    "v4",
    "pnpm/action-setup":            "v4",
    "cloudflare/wrangler-action":   "v3",
    "docker/login-action":          "v3",
    "docker/metadata-action":       "v5",
    "docker/build-push-action":     "v5",
    "softprops/action-gh-release":  "v2",
}

# ── Package manager config ─────────────────────────────────────────────────────

PKG: dict[str, dict] = {
    "pnpm": {
        "install":    "pnpm install",
        "run":        "pnpm",
        "cache":      "pnpm",
        "extra_step": "pnpm/action-setup",
    },
    "npm": {
        "install":    "npm ci",
        "run":        "npm run",
        "cache":      "npm",
        "extra_step": None,
    },
    "yarn": {
        "install":    "yarn install --frozen-lockfile",
        "run":        "yarn",
        "cache":      "yarn",
        "extra_step": None,
    },
}

# ── Workflow name + filename per template / publish target ─────────────────────

WORKFLOW_META = {
    "1": {
        "name":     "CI",
        "filename": "ci.yml",
    },
    "2": {
        "cf-pages":  ("Deploy to Cloudflare Pages",  "deploy-frontend-to-cloudflare.yml"),
        "cf-worker": ("Deploy to Cloudflare Worker", "deploy-backend-to-cloudflare.yml"),
        "github":    ("Release",                     "release.yml"),
    },
    "3": {
        "name":     "Docker",
        "filename": "docker.yml",
    },
    "4": {
        "name":     "PR",
        "filename": "pr.yml",
    },
}


# ── Param + interactive helpers ────────────────────────────────────────────────

class UserAbort(Exception):
    pass

_QUIT = {"q", "quit", "exit"}

@dataclass
class Param:
    key:     str
    prompt:  str
    default: str
    choices: list[str] | None = None


def ask(param: Param) -> str:
    if param.choices:
        parts = []
        for i, c in enumerate(param.choices, 1):
            label = f"{i}.{c}"
            parts.append(f"[{label}]" if c == param.default else label)
        opts = "/".join(parts)
        line = f"  {param.prompt} ({opts}): "
    else:
        hint = "  (blank to skip)" if param.default == "" else f"  [{param.default}]"
        line = f"  {param.prompt}{hint}: "
    try:
        val = input(line).strip()
    except (EOFError, KeyboardInterrupt):
        raise UserAbort
    if val.lower() in _QUIT:
        raise UserAbort
    if not val:
        return param.default
    # numeric shortcut: "1" → first choice, etc.
    if param.choices and val.isdigit():
        idx = int(val) - 1
        if 0 <= idx < len(param.choices):
            return param.choices[idx]
    return val


def ask_yn(prompt: str, default: bool = False) -> bool:
    opts = "Y/n" if default else "y/N"
    try:
        val = input(f"  {prompt} [{opts}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        raise UserAbort
    if val in _QUIT:
        raise UserAbort
    return (val in ("y", "yes")) if val else default


# ── Version injection ──────────────────────────────────────────────────────────

def inject_versions(yaml_str: str, versions: dict) -> tuple[str, list[str]]:
    """Pin every `uses: owner/repo` (bare or already versioned) from versions.json."""
    warnings: list[str] = []

    def _pin(m: re.Match) -> str:
        action = m.group(1)
        key    = "/".join(action.split("/")[:2])
        ver    = versions.get(key) or versions.get(action)
        if not ver:
            ver = FALLBACKS.get(key) or FALLBACKS.get(action)
            if ver:
                warnings.append(f"  [fallback] {action}@{ver}")
            else:
                warnings.append(f"  [missing]  {action} — left unpinned")
                return m.group(0)
        # v-prefixed: keep major version only (e.g. v6.0.2 → v6)
        if ver.startswith("v") and re.match(r"v\d+\.\d+", ver):
            ver = "v" + ver[1:].split(".")[0]
        return f"uses: {action}@{ver}"

    result = re.sub(r"uses:\s+([\w./-]+)(?:@[\w.]+)?", _pin, yaml_str)
    return result, warnings


# ── Shared YAML blocks ─────────────────────────────────────────────────────────

def _node_steps_ci(pkg_name: str, node_ver: str, pnpm_ver: str = "10") -> str:
    """CI pattern: pnpm/action-setup → setup-node (with cache) → install."""
    cfg   = PKG[pkg_name]
    lines = ["      - uses: actions/checkout"]

    if cfg["extra_step"]:
        lines += [
            "",
            f"      - uses: {cfg['extra_step']}",
            "        with:",
            f"          version: {pnpm_ver}",
        ]

    lines += [
        "",
        "      - uses: actions/setup-node",
        "        with:",
        f"          node-version: {node_ver}",
        f"          cache: '{cfg['cache']}'",
        "",
        f"      - run: {cfg['install']}",
    ]
    return "\n".join(lines)


def _node_steps_deploy(pkg_name: str, node_ver: str, pnpm_ver: str = "10") -> str:
    """Deploy pattern: setup-node → pnpm/action-setup → install (no cache)."""
    cfg   = PKG[pkg_name]
    lines = [
        "      - uses: actions/checkout",
        "",
        "      - uses: actions/setup-node",
        "        with:",
        f"          node-version: {node_ver}",
    ]

    if cfg["extra_step"]:
        lines += [
            "",
            f"      - uses: {cfg['extra_step']}",
            "        with:",
            f"          version: {pnpm_ver}",
        ]

    lines += [
        "",
        f"      - run: {cfg['install']}",
    ]
    return "\n".join(lines)


def _concurrency(group_expr: str | None = None) -> str:
    suffix = group_expr or G["ref"]
    return (
        "concurrency:\n"
        f"  group: {G['workflow']}-{suffix}\n"
        "  cancel-in-progress: true"
    )



# ══════════════════════════════════════════════════════════════════════════════
# Templates
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. CI ──────────────────────────────────────────────────────────────────────

CI_PARAMS = [
    Param("node_version", "Node.js version", "24"),
    Param("pkg_manager",  "Package manager", "pnpm", ["pnpm", "npm", "yarn"]),
    Param("branches",     "Trigger branches", "main"),
    Param("test_cmd",     "Test script",      "test"),
    Param("lint_cmd",     "Lint script",      "lint"),
    Param("build_cmd",    "Build script",     ""),
]


def ci_template(p: dict) -> str:
    cfg  = PKG[p["pkg_manager"]]
    run  = cfg["run"]
    lint  = f"\n      - run: {run} {p['lint_cmd']}"  if p["lint_cmd"]  else ""
    build = f"\n      - run: {run} {p['build_cmd']}" if p["build_cmd"] else ""

    if p.get("matrix"):
        node_ver = G["matrix_node"]
        strategy = (
            "    strategy:\n"
            "      matrix:\n"
            f"        node: [{p['matrix_versions']}]\n"
        )
    else:
        node_ver = p["node_version"]
        strategy = ""

    return f"""name: {p['workflow_name']}

on:
  push:
    branches: [{p['branches']}]
  pull_request:

permissions:
  contents: read

{_concurrency()}

jobs:
  test:
    runs-on: ubuntu-latest
{strategy}    steps:
{_node_steps_ci(p["pkg_manager"], node_ver, p.get("pnpm_version", "10"))}{lint}

      - run: {run} {p['test_cmd']}{build}
"""


# ── 2. Release / Deploy ────────────────────────────────────────────────────────

RELEASE_PARAMS = [
    Param("node_version",    "Node.js version",  "24"),
    Param("pkg_manager",     "Package manager",  "pnpm", ["pnpm", "npm", "yarn"]),
    Param("build_cmd",       "Build script",     "build"),
    Param("publish_target",  "Publish target",   "cf-pages",
          ["cf-pages", "cf-worker", "github"]),
]


def _cf_config_step(p: dict) -> str:
    return f"""
      - name: Determine Cloudflare config
        id: cf
        run: |
          if [[ "{G['gh_env']}" == "dev" ]]; then
            echo "domain={p['dev_domain']}" >> $GITHUB_OUTPUT
          else
            echo "domain={p['release_domain']}" >> $GITHUB_OUTPUT
          fi"""


def _cf_deploy_step(p: dict, target: str) -> str:
    run_cmd = PKG[p["pkg_manager"]]["run"]
    step_name = "Deploy to Cloudflare Pages" if target == "cf-pages" else "Deploy to Cloudflare Worker"
    return f"""
      - name: {step_name}
        env:
          CLOUDFLARE_API_TOKEN: ${{{{ secrets.CLOUDFLARE_API_TOKEN }}}}
          CLOUDFLARE_ACCOUNT_ID: ${{{{ secrets.CLOUDFLARE_ACCOUNT_ID }}}}
        run: |
          if [[ "{G['gh_env']}" == "dev" ]]; then
            {run_cmd} {p['dev_deploy_cmd']}
          else
            {run_cmd} {p['prod_deploy_cmd']}
          fi"""


def _deploy_summary() -> str:
    return f"""
      - name: Deployment summary
        run: |
          cat << EOF >> $GITHUB_STEP_SUMMARY
          ## ✅ Deployed

          - 🚀 Deployment completed!
          - 🔧 Environment: {G['gh_env']}
          - 🌿 Branch: {G['ref_name']}
          - 🌐 Domain: https://{G['step_cf_domain']}
          EOF"""


def _deploy_summary_no_domain() -> str:
    return f"""
      - name: Deployment summary
        run: |
          cat << EOF >> $GITHUB_STEP_SUMMARY
          ## ✅ Deployed

          - 🚀 Deployment completed!
          - 🔧 Environment: {G['gh_env']}
          - 🌿 Branch: {G['ref_name']}
          EOF"""


def _cf_trigger_header(workflow_name: str) -> str:
    return f"""name: {workflow_name}

on:
  push:
    branches:
      - dev
      - dev*
      - release
      - release*
  workflow_dispatch:
    inputs:
      environment:
        description: Environment
        required: true
        default: dev
        type: choice
        options:
          - dev
          - release

permissions:
  contents: read
  deployments: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: {G['deploy_env']}
    env:
      GH_ENV: {G['deploy_env']}

    steps:"""


def cf_pages_template(p: dict) -> str:
    return f"""{_cf_trigger_header(p['workflow_name'])}
{_node_steps_deploy(p["pkg_manager"], p["node_version"], p.get("pnpm_version", "10"))}

      - run: pnpm install -g wrangler

      - run: {PKG[p["pkg_manager"]]["run"]} {p["build_cmd"]}
{_cf_config_step(p)}
{_cf_deploy_step(p, "cf-pages")}
{_deploy_summary()}
"""


def cf_worker_template(p: dict) -> str:
    return f"""{_cf_trigger_header(p['workflow_name'])}
{_node_steps_deploy(p["pkg_manager"], p["node_version"], p.get("pnpm_version", "10"))}

      - run: pnpm install -g wrangler
{_cf_deploy_step(p, "cf-worker")}
{_deploy_summary_no_domain()}
"""


def github_release_template(p: dict) -> str:
    cfg = PKG[p["pkg_manager"]]
    return f"""name: {p['workflow_name']}

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
{_node_steps_ci(p["pkg_manager"], p["node_version"], p.get("pnpm_version", "10"))}

      - run: {cfg["run"]} {p["build_cmd"]}

      - name: Create GitHub Release
        uses: softprops/action-gh-release
        with:
          generate_release_notes: true
"""


def release_template(p: dict) -> str:
    target = p["publish_target"]
    if target == "cf-pages":
        return cf_pages_template(p)
    elif target == "cf-worker":
        return cf_worker_template(p)
    else:
        return github_release_template(p)


# ── 3. Docker ──────────────────────────────────────────────────────────────────

DOCKER_PARAMS = [
    Param("registry",   "Registry",          "ghcr.io", ["ghcr.io", "docker.io"]),
    Param("image_name", "Image name",        G["repo"]),
    Param("dockerfile", "Dockerfile path",   "Dockerfile"),
    Param("context",    "Build context",     "."),
    Param("platforms",  "Platforms",         "linux/amd64"),
    Param("branches",   "Trigger branches",  "main"),
]


def docker_template(p: dict) -> str:
    if p["registry"] == "ghcr.io":
        login_with = (
            f"          username: {G['actor']}\n"
            f"          password: {G['token']}"
        )
    else:
        login_with = (
            "          username: ${{ secrets.DOCKER_USERNAME }}\n"
            "          password: ${{ secrets.DOCKER_PASSWORD }}"
        )

    return f"""name: {p['workflow_name']}

on:
  push:
    branches: [{p['branches']}]
    tags: ['v*']

permissions:
  contents: read
  packages: write

env:
  REGISTRY: {p['registry']}
  IMAGE_NAME: {p['image_name']}

{_concurrency()}

jobs:
  build-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout

      - name: Log in to {p['registry']}
        uses: docker/login-action
        with:
{login_with}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action
        with:
          images: {p['registry']}/{p['image_name']}

      - name: Build and push
        uses: docker/build-push-action
        with:
          context: {p['context']}
          file: {p['dockerfile']}
          push: true
          tags: {G['meta_tags']}
          labels: {G['meta_labels']}
          platforms: {p['platforms']}
"""


# ── 4. PR Checks ───────────────────────────────────────────────────────────────

PR_PARAMS = [
    Param("node_version",  "Node.js version",   "24"),
    Param("pkg_manager",   "Package manager",   "pnpm", ["pnpm", "npm", "yarn"]),
    Param("lint_cmd",      "Lint script",       "lint"),
    Param("typecheck_cmd", "Type-check script", "typecheck"),
]


def pr_template(p: dict) -> str:
    cfg = PKG[p["pkg_manager"]]
    run = cfg["run"]
    typecheck = f"\n      - run: {run} {p['typecheck_cmd']}" if p["typecheck_cmd"] else ""

    return f"""name: {p['workflow_name']}

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read

{_concurrency(G['pr_ref'])}

jobs:
  pr-check:
    runs-on: ubuntu-latest
    steps:
{_node_steps_ci(p["pkg_manager"], p["node_version"], p.get("pnpm_version", "10"))}

      - run: {run} {p['lint_cmd']}{typecheck}
"""


# ══════════════════════════════════════════════════════════════════════════════
# Template registry
# ══════════════════════════════════════════════════════════════════════════════

TEMPLATES = {
    "1": ("CI / Test",           CI_PARAMS,      ci_template),
    "2": ("Release / Deploy",    RELEASE_PARAMS, release_template),
    "3": ("Docker Build & Push", DOCKER_PARAMS,  docker_template),
    "4": ("PR Checks",           PR_PARAMS,      pr_template),
}


# ── Interactive flow ───────────────────────────────────────────────────────────

def collect_params(params: list[Param]) -> dict:
    return {p.key: ask(p) for p in params}


def run_interactive(versions: dict, out_dir: Path) -> None:
    print(f"\n  GitHub Actions Workflow Generator")
    print(f"  {'─' * 42}")
    for key, (label, _, _) in TEMPLATES.items():
        print(f"  {key}  {label}")
    print(f"  {'─' * 42}")
    print(f"  (type q to quit at any prompt)")

    try:
        choice = input("  Select template [1-4]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return

    if choice.lower() in _QUIT:
        print("  Aborted.")
        return

    if choice not in TEMPLATES:
        print(f"  Invalid choice: {choice!r}")
        return

    label, params, render = TEMPLATES[choice]
    print(f"\n  ── {label} ──\n")

    try:
        p = collect_params(params)

        # ── pnpm version (asked only when pnpm is selected) ───────────────────────
        if p.get("pkg_manager") == "pnpm":
            p["pnpm_version"] = ask(Param("pnpm_version", "pnpm version", "10"))

        # ── Template-specific extras ───────────────────────────────────────────────
        if choice == "1":  # CI
            if ask_yn("Enable matrix strategy (multiple Node versions)?"):
                p["matrix"]          = True
                p["matrix_versions"] = ask(Param("mv", "Node versions (comma-separated)", "20, 22, 24"))
            else:
                p["matrix"] = False

        if choice == "2":  # Release / Deploy
            target = p["publish_target"]
            if target == "cf-pages":
                print()
                # CI domain: auto-expand prefix → prefix.aceapp.dev
                raw_dev = ask(Param("dev_domain", "Dev domain", "project.aceapp.dev"))
                dev_domain = raw_dev if "." in raw_dev else f"{raw_dev}.aceapp.dev"
                p["dev_domain"] = dev_domain

                # Release domain: smart-derive from dev domain, user can override
                if ".aceapp.dev" in dev_domain:
                    release_default = dev_domain.replace(".aceapp.dev", ".ropean.org")
                else:
                    release_default = "project.ropean.org"
                p["release_domain"] = ask(Param("release_domain", "Release domain", release_default))

                p["dev_deploy_cmd"]  = ask(Param("dev_deploy_cmd",  "Dev deploy script",     "ship:dev:frontend"))
                p["prod_deploy_cmd"] = ask(Param("prod_deploy_cmd", "Release deploy script",  "ship:prod:frontend"))

            elif target == "cf-worker":
                print()
                p["dev_deploy_cmd"]  = ask(Param("dev_deploy_cmd",  "Dev deploy script",     "ship:dev:backend"))
                p["prod_deploy_cmd"] = ask(Param("prod_deploy_cmd", "Release deploy script",  "ship:prod:backend"))

        # ── Auto-generate workflow name + filename ─────────────────────────────────
        meta = WORKFLOW_META[choice]
        if choice == "2":
            wf_name, default_filename = meta[p["publish_target"]]
        else:
            wf_name, default_filename = meta["name"], meta["filename"]

        p["workflow_name"] = wf_name

        # ── Output filename ────────────────────────────────────────────────────────
        print()
        filename = ask(Param("filename", "Output filename", default_filename))
        if not filename.endswith((".yml", ".yaml")):
            filename += ".yml"

        # ── Render + inject versions ───────────────────────────────────────────────
        yaml_str        = render(p)
        yaml_str, warns = inject_versions(yaml_str, versions)

        if warns:
            print("\n  Version notes:")
            for w in warns:
                print(w)

        # ── Write ──────────────────────────────────────────────────────────────────
        out_path = out_dir / filename
        if out_path.exists():
            if not ask_yn(f"  {out_path} already exists. Overwrite?", default=True):
                print("  Not written.")
                return
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(yaml_str, encoding="utf-8", newline="\n")
        print(f"  OK  {out_path}")

    except UserAbort:
        print("\n  Aborted.")


# ── Entry point ────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Interactive GitHub Actions workflow generator."
    )
    p.add_argument(
        "-o", "--output",
        default=".github/workflows",
        metavar="DIR",
        help="Output directory (default: .github/workflows/)",
    )
    p.add_argument(
        "-v", "--versions",
        default=str(DEFAULT_VERSIONS),
        metavar="FILE",
        help=f"Versions JSON file (default: {DEFAULT_VERSIONS.name})",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    versions_path = Path(args.versions)
    if versions_path.exists():
        versions: dict = json.loads(versions_path.read_text(encoding="utf-8"))
        print(f"[versions] {len(versions)} entries from {versions_path.name}",
              file=sys.stderr)
    else:
        versions = {}
        print(f"[warn] {versions_path.name} not found — using built-in fallbacks only",
              file=sys.stderr)

    run_interactive(versions, Path(args.output))


if __name__ == "__main__":
    main()
