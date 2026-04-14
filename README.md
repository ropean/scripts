# Scripts Collection

> A curated collection of production-ready scripts for modern development workflows

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-live-brightgreen.svg)](https://scripts.aceapp.dev/)

## 📖 About

Practical, documented scripts that solve real-world development problems. Each script follows a standardized format with metadata headers, inline comments, and usage examples.

## 🌐 Documentation

Browse the complete collection with syntax highlighting, search, and categorization:

- 🚀 **Primary**: [scripts.aceapp.dev](https://scripts.aceapp.dev/)
- ⚡ **Mirror**: Cloudflare Pages (faster global access)

## 📂 Scripts

### 🎨 Javascript

| Script | Description |
|--------|-------------|
| `intercept-requests.js` | Intercepts and redirects Decap CMS authentication requests to local development server |
| `react-select-auto-selector.js` | Automatically selects options in React Select dropdowns with priority for "Edit" options |

### ⚙️ Node.js

| Script | Description |
|--------|-------------|
| `local-proxy.js` | Proxy server for Decap CMS with Hugo, handling local authentication |

### 🔧 Git

| Script | Description |
|--------|-------------|
| `git-change-all-authors.sh` | Standardize author information across ALL commits in a repository |
| `git-change-all-authors-fast.sh` | High-performance author standardization for large repositories |
| `git-change-commit.sh` | Modify author/message for ONE specific commit in Git history |
| `git-change-pr-authors.sh` | Modify author and committer information for commits in a PR branch |
| `git-lfs-config-generator.sh` | Generate smart `.gitattributes` configuration for Git LFS based on file sizes |
| `git-squash-to-single-commit.sh` | Create a fresh repository with a single commit, preserving current state |
| `git-submodules.sh` | Complete toolkit for managing Git submodules with bulk operations |

### ⚡ Serverless

| Script | Description |
|--------|-------------|
| `cloudflare-setup.js` | Automated setup tool for Cloudflare Workers resources (KV, R2, D1, Secrets) |

### 🗄️ Database

| Script | Description |
|--------|-------------|
| `setup-supabase-db.sh` | Interactive script to create a dedicated database and user in Supabase PostgreSQL |

### 🐍 Python

| Script | Description |
|--------|-------------|
| `git-clean-ignored.py` | Scan a directory for Git repos and clean all gitignored files, safely |
| `git-lfs-auto.py` | Scan a directory for large files and register them with Git LFS |
| `git-status-all.py` | Check Git status for every repository under a root directory |

### 🔑 Utilities

| Script | Description |
|--------|-------------|
| `chmod.sh` | Recursively set execute permissions for all shell scripts |

## 🚀 Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/ropean/scripts.git
cd scripts

# Install dependencies
pnpm install

# Generate documentation
pnpm run generate

# Start development server
pnpm dev

# Build for production
pnpm build
```

> **Requires**: [pnpm](https://pnpm.io/) — install with `npm install -g pnpm`

## ✍️ Contributing Scripts

### 1. Place Your Script

Put it in the matching category under `script-files/`:

```
script-files/
├── javascript/   # Browser & UI scripts
├── nodejs/       # Server-side & Node.js tools
├── git/          # Version control automation
├── serverless/   # Cloudflare Workers, AWS Lambda, etc.
├── database/     # DB utilities and SQL scripts
└── python/       # Python automation & utilities
```

Create a new directory if none of the above fit, then add a `.config.js` alongside it:

```javascript
module.exports = {
  title: "Category Title",
  description: "Brief description of this category",
  icon: "🎯",
  order: 70, // controls display order
};
```

### 2. Add a Metadata Header

**JavaScript / Node.js:**

```javascript
/**
 * @title Your Script Title
 * @description Brief one-line description
 * @version 1.0.0
 * @author Your Name
 *
 * Detailed explanation of what this script does and when to use it.
 *
 * @example
 * node your-script.js
 *
 * @requires dependency1, dependency2
 * @note Important notes or warnings
 */
```

**Shell / Bash:**

```bash
#!/bin/bash
# @title Your Script Title
# @description Brief one-line description
# @version 1.0.0
# @author Your Name
#
# @example
# ./your-script.sh
```

**Python:**

```python
#!/usr/bin/env python3
"""
@title Your Script Title
@description Brief one-line description
@version 1.0.0
@author Your Name

@example
python your-script.py
"""
```

See [Script Format Specification](/help/script-template) for the full reference.

### 3. Generate & Verify

```bash
pnpm run generate   # rebuilds docs, sidebar, nav, and homepage
pnpm dev            # preview locally
```

### 4. Submit

```bash
git add script-files/<category>/your-script.*
git commit -m "Add: brief description"
# open a pull request targeting the release branch
```

## 🏗️ Project Structure

```
scripts/
├── script-files/             # All scripts, organized by category
│   ├── javascript/
│   ├── nodejs/
│   ├── git/
│   ├── serverless/
│   ├── database/
│   └── python/
├── md-files/                 # Hand-written documentation pages
├── docs/                     # VitePress site (auto-generated)
│   ├── .vitepress/
│   │   ├── config.mjs        # Site configuration
│   │   ├── sidebar.json      # Auto-generated sidebar
│   │   └── nav.json          # Auto-generated navigation
│   ├── index.md              # Homepage (auto-generated features)
│   └── public/
├── scripts/
│   ├── generate-docs.js      # Main doc generator
│   ├── generate-features.js  # Feature flags generator
│   └── generate-robots.mjs   # robots.txt generator
└── .github/workflows/        # CI/CD pipelines
```

## 🔧 Documentation System

`pnpm run generate` does everything automatically:

1. Scans all `script-files/` category directories
2. Extracts `@tags` metadata from each script header
3. Generates individual markdown pages per script
4. Rebuilds sidebar, navigation, and **homepage features** to match current categories
5. Sorts all navigation by the `order` field in `.config.js`

## 🌍 Deployment

| Target | Branch | URL |
|--------|--------|-----|
| GitHub Pages | `release` | [scripts.aceapp.dev](https://scripts.aceapp.dev/) |
| Cloudflare Pages | `release` | Mirror (faster global CDN) |

Both run automatically via GitHub Actions on push to `release`.

## 📄 License

MIT — see [LICENSE](./LICENSE) for details.

---

**Made with ❤️ by [ropean](https://ropean.org/)** | _Sharing excellence in code, one script at a time_
