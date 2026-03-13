# Scripts Collection

> A curated collection of production-ready scripts and code examples for modern web development

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-live-brightgreen.svg)](https://scripts.aceapp.dev/)

## 📖 About

This repository contains a carefully curated collection of practical scripts, utilities, and code examples designed to solve real-world development challenges. Each script is documented, tested, and ready to use in your projects.

## 🌐 Documentation

Browse the complete collection with syntax highlighting, search, and categorization:

- 🚀 **Primary**: [GitHub Pages](https://scripts.aceapp.dev/scripts/)
- ⚡ **Mirror**: Cloudflare Pages (faster for global access)

## 📂 Categories

Our scripts are organized into focused categories:

### 🎨 Frontend

React components, DOM manipulation, browser utilities, and UI patterns

- Decap CMS authentication interceptor
- React Select auto-selector for automation
- _[View all frontend scripts →](https://scripts.aceapp.dev/scripts/frontend/)_

### ⚙️ Backend

Server-side utilities, API helpers, and Node.js tools

- Local development proxy server
- Authentication middleware
- _[View all backend scripts →](https://scripts.aceapp.dev/scripts/backend/)_

### 🔧 Git

Version control automation and repository management

- Smart Git LFS configuration generator
- Submodules management toolkit
- _[View all git tools →](https://scripts.aceapp.dev/scripts/git/)_

### 📦 Node.js

Development tools, build utilities, and infrastructure scripts

- Cloudflare Workers environment setup
- Package management helpers
- _[View all Node.js scripts →](https://scripts.aceapp.dev/scripts/node/)_

## 🚀 Quick Start

### Using Scripts

1. Browse the [documentation site](https://scripts.aceapp.dev/scripts/)
2. Find a script that solves your problem
3. Copy the code or download the file
4. Follow the usage instructions in the script header

### Local Development

```bash
# Clone the repository
git clone https://github.com/ropean/scripts.git
cd scripts

# Install dependencies
npm install

# Generate documentation
npm run generate

# Start development server
npm run docs:dev

# Build for production
npm run docs:build
```

## ✍️ Contributing Scripts

We welcome high-quality contributions! Here's how to add a new script:

### 1. Choose the Right Category

Place your script in the appropriate directory:

- `frontend/` - Browser and UI-related scripts
- `backend/` - Server-side and Node.js scripts
- `git/` - Version control tools
- `node/` - Build tools and utilities

Or create a new category directory if needed.

### 2. Follow the Script Format

Every script must include a standardized header with `@tags`:

```javascript
/**
 * @title Your Script Title
 * @description Brief one-line description
 * @version 1.0.0
 * @author Your Name
 *
 * Detailed explanation of what this script does,
 * how it works, and when to use it.
 *
 * @example
 * node your-script.js
 *
 * @requires dependency1, dependency2
 * @note Important notes or warnings
 */
```

For shell scripts:

```bash
#!/bin/bash

# @title Your Script Title
# @description Brief one-line description
# @version 1.0.0
# @author Your Name
#
# Detailed explanation here
#
# @example
# ./your-script.sh
```

📚 See [.script-template.md](./.script-template.md) for complete format specification.

### 3. Add Category Configuration (if new category)

Create `.config.js` in your category directory:

```javascript
module.exports = {
  title: "Category Title",
  description: "Brief description of this category",
  icon: "🎯", // Choose an appropriate emoji
};
```

### 4. Test and Submit

```bash
# Generate docs to verify formatting
npm run generate

# Build to ensure no errors
npm run docs:build

# Commit your changes
git add .
git commit -m "Add: your script description"

# Create pull request to 'release' branch
```

## 🏗️ Project Structure

```text
scripts/
├── .script-template.md       # Script format specification
├── frontend/                 # Frontend scripts
│   ├── .config.js            # Category configuration
│   └── *.js                 # Script files
├── backend/                  # Backend scripts
├── git/                      # Git tools
├── node/                     # Node.js utilities
├── docs/                     # VitePress documentation
│   ├── .vitepress/
│   │   ├── config.mjs       # Site configuration
│   │   ├── sidebar.json     # Auto-generated sidebar
│   │   └── nav.json         # Auto-generated navigation
│   └── public/
│       └── logo.svg         # Site logo
├── scripts/
│   └── generate-docs.js     # Documentation generator
└── .github/workflows/       # CI/CD pipelines
```

## 🔧 Documentation System

The documentation is automatically generated from script files:

1. **Dynamic Scanning**: Automatically discovers all category directories
2. **Metadata Extraction**: Parses `@tags` from script headers
3. **Markdown Generation**: Creates individual pages for each script
4. **Navigation Updates**: Dynamically builds sidebar and nav menus
5. **SEO Optimization**: Adds meta tags and sitemaps
6. **Build Optimization**: Minifies and compresses output

## 🌍 Deployment

### GitHub Pages (Default)

Automatically deploys on push to `release` branch via GitHub Actions.

**URL**: <https://scripts.aceapp.dev/scripts/>

### Cloudflare Pages (Alternative)

Faster global access with unlimited bandwidth.

**Setup**: See [CLOUDFLARE_DEPLOYMENT.md](./CLOUDFLARE_DEPLOYMENT.md)

Both deployments can run simultaneously for redundancy.

## 📋 Script Format Features

Our standardized format ensures consistency and discoverability:

- **Required Tags**: `@title`, `@description`
- **Optional Tags**: `@author`, `@version`, `@example`, `@requires`, `@note`, `@see`
- **Auto-generated**:
  - Syntax highlighting
  - Category classification
  - Metadata sections
  - GitHub source links

## 🎯 Quality Standards

All scripts in this repository follow these principles:

✅ **Production-Ready**: Tested and reliable code
✅ **Well-Documented**: Clear headers and inline comments
✅ **Self-Contained**: Minimal external dependencies
✅ **Best Practices**: Modern JavaScript/Bash conventions
✅ **Practical**: Solves real-world problems

## 🤝 Contributing

Contributions are welcome! Please:

1. Read the [script format specification](./.script-template.md)
2. Ensure your code follows best practices
3. Add comprehensive documentation
4. Test locally before submitting
5. Submit PR to the `release` branch

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

Built with:

- [VitePress](https://vitepress.dev/) - Documentation framework
- [GitHub Actions](https://github.com/features/actions) - CI/CD
- [Cloudflare Pages](https://pages.cloudflare.com/) - Fast global deployment

## 📬 Contact

- **Issues**: [GitHub Issues](https://github.com/ropean/scripts/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ropean/scripts/discussions)
- **Website**: [ropean.org](https://ropean.org/)

---

**Made with ❤️ by [ropean](https://ropean.org/)** | _Sharing excellence in code, one script at a time_
