# Scripts Collection

A curated collection of excellent JavaScript code examples for both frontend and backend development.

## 📚 Documentation Website

Visit our beautiful documentation site with syntax highlighting and search:
- **GitHub Pages**: https://ropean.github.io/scripts/
- **Cloudflare Pages**: (configure after deployment)

## About

This repository is dedicated to sharing high-quality, practical JavaScript code snippets and examples that demonstrate best practices in modern web development. Whether you're working on the client-side or server-side, you'll find useful patterns and implementations here.

## What You'll Find

- **Frontend Examples**: React components, vanilla JavaScript utilities, DOM manipulation, and modern UI patterns
- **Backend Examples**: Node.js applications, API implementations, database integrations, and server-side utilities
- **Full-Stack Projects**: End-to-end examples showcasing complete application architectures
- **Best Practices**: Code that emphasizes clean architecture, performance, and maintainability

## Goals

- Share production-ready JavaScript code
- Demonstrate modern JavaScript features and patterns
- Provide reference implementations for common use cases
- Help developers learn from real-world examples

## 🚀 Local Development

```bash
# Install dependencies
npm install

# Generate documentation from scripts
npm run generate

# Start development server
npm run docs:dev

# Build for production
npm run docs:build
```

## 📦 Adding New Scripts

1. Add your script to the appropriate category folder:
   - `frontend/` - Frontend scripts and utilities
   - `backend/` - Backend and server-side scripts
   - `git/` - Git automation and tools
   - `node/` - Node.js utilities and tools

2. Include descriptive comments at the top:
   ```javascript
   /**
    * Script Title
    * Detailed description of what this script does
    * and how it works
    */
   ```

3. Push to the `release` branch - documentation will be auto-generated and deployed!

## 🌐 Deployment

### GitHub Pages (Default)
- Automatically deploys on push to `release` branch
- Workflow: `.github/workflows/deploy-pages.yml`
- URL: https://ropean.github.io/scripts/

### Cloudflare Pages (Alternative)
- Faster global access, especially in China
- See [CLOUDFLARE_DEPLOYMENT.md](./CLOUDFLARE_DEPLOYMENT.md) for setup
- Workflow: `.github/workflows/deploy-cloudflare.yml`

## Contributing

Contributions are welcome! If you have excellent JavaScript code to share:

1. Ensure your code follows modern JavaScript best practices
2. Include clear documentation and comments in your code
3. Add examples or usage instructions as comments
4. Submit a pull request to the `release` branch

## License

MIT

## Contact

For questions or suggestions, please open an issue or reach out through [your preferred contact method].

---

_Sharing excellence in JavaScript, one commit at a time._
