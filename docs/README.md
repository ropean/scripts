# Scripts Collection Documentation

This directory contains the VitePress documentation site for the scripts collection.

## Development

```bash
# Install dependencies
npm install

# Generate documentation from scripts
npm run generate

# Start development server
npm run docs:dev

# Build for production
npm run docs:build

# Preview production build
npm run docs:preview
```

## How It Works

1. **Automatic Scanning**: The `scripts/generate-docs.js` script scans all category folders (frontend, backend, git, node)
2. **Metadata Extraction**: It extracts titles, descriptions, and usage instructions from script comments
3. **Page Generation**: Creates a markdown page for each script with syntax-highlighted code
4. **Sidebar Updates**: Automatically updates the VitePress sidebar configuration
5. **Deployment**: GitHub Actions builds and deploys to GitHub Pages on release branch updates

## Adding New Scripts

1. Add your script to the appropriate category folder (frontend, backend, git, or node)
2. Include descriptive comments at the top of your file
3. Optionally add a USAGE INSTRUCTIONS section in comments
4. Push to the release branch - documentation will be auto-generated and deployed

## Manual Regeneration

If you want to regenerate the documentation manually:

```bash
npm run generate
```

This will rescan all scripts and update the documentation pages.
