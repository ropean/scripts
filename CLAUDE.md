# CLAUDE.md — scripts repo

## Script Format

**Always follow `md-files/help/script-template.md` when writing any script.**

Every script must include the standard header block:
- Python: `#!/usr/bin/env python3` + docstring with `@title`, `@description`, `@example`
- Shell: `#!/bin/bash` + comment block with same tags
- JS: JSDoc block with same tags

Use the author line: `@author ropean, Claude Sonnet (Anthropic)`

## Repo Layout

| Dir | Purpose |
|-----|---------|
| `script-files/python/` | Python scripts |
| `script-files/` | Other language scripts |
| `md-files/help/` | Documentation / spec files |

## Conventions (Python)

- Use `argparse` for CLI; support both positional args and interactive prompts when args are missing.
- Path handling: always resolve via `pathlib.Path` + `resolve_path()` from `path-utils.py` (handles Windows, macOS, Linux, WSL paths).
- Colors: use the `_supports_color()` / ANSI pattern seen in `git-status-all.py`.
- Section separators: `# ════════════════════════════════════════════════════════════`.
