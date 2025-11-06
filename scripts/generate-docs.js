#!/usr/bin/env node

/**
 * Auto-generate VitePress documentation from script files
 * Scans frontend, backend, git, node directories and creates markdown pages
 */

const fs = require("fs");
const path = require("path");

// Configuration
const CATEGORIES = ["frontend", "backend", "git", "node"];
const ROOT_DIR = path.join(__dirname, "..");
const DOCS_DIR = path.join(ROOT_DIR, "docs");
const SIDEBAR_FILE = path.join(DOCS_DIR, ".vitepress", "sidebar.json");

// Category display names and descriptions
const CATEGORY_INFO = {
  frontend: {
    title: "Frontend Scripts",
    description:
      "React components, vanilla JavaScript utilities, DOM manipulation, and modern UI patterns",
    icon: "🎨",
  },
  backend: {
    title: "Backend Scripts",
    description:
      "Node.js applications, API implementations, database integrations, and server-side utilities",
    icon: "⚙️",
  },
  git: {
    title: "Git Tools",
    description:
      "Git automation scripts, LFS configuration, submodule management, and workflow utilities",
    icon: "🔧",
  },
  node: {
    title: "Node Utilities",
    description:
      "Node.js utilities, package management, deployment tools, and infrastructure scripts",
    icon: "📦",
  },
};

/**
 * Extract metadata from script file
 * @param {string} filePath - Path to the script file
 * @returns {object} Metadata object with title, description, usage, etc.
 */
function extractMetadata(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const lines = content.split("\n");

  let title = "";
  let description = [];
  let usageInstructions = [];
  let inUsageBlock = false;
  let inDescBlock = false;

  // Extract from file header
  for (let i = 0; i < Math.min(150, lines.length); i++) {
    const line = lines[i].trim();

    // Extract title from first comment or filename
    if (!title && (line.startsWith("//") || line.startsWith("*"))) {
      const text = line.replace(/^(\/\/|\/?\*+)\s*/, "").trim();
      if (text && !text.startsWith("@") && text.length < 100) {
        title = text;
      }
    }

    // Extract description from JSDoc
    if (line.startsWith("/**") || line.startsWith("*")) {
      const text = line
        .replace(/^(\/\*\*|\/?\*+)\s*/, "")
        .replace(/\*\/$/, "")
        .trim();
      if (text && !text.startsWith("@") && !inUsageBlock) {
        if (
          text.toUpperCase().includes("USAGE") ||
          text.toUpperCase().includes("INSTRUCTIONS")
        ) {
          inUsageBlock = true;
        } else if (text) {
          description.push(text);
          inDescBlock = true;
        }
      }
    } else if (inDescBlock && !line.startsWith("//") && !line.startsWith("*")) {
      inDescBlock = false;
    }

    // Extract usage instructions
    if (inUsageBlock && (line.startsWith("*") || line.startsWith("//"))) {
      const text = line
        .replace(/^(\/\/|\/?\*+)\s*/, "")
        .replace(/\*\/$/, "")
        .trim();
      if (text) {
        usageInstructions.push(text);
      }
    }

    // Stop at first code line (non-comment, non-empty)
    if (
      line &&
      !line.startsWith("//") &&
      !line.startsWith("/*") &&
      !line.startsWith("*") &&
      !line.startsWith("const") &&
      !line.startsWith("import") &&
      !line.startsWith("require")
    ) {
      if (description.length > 0 || title) break;
    }
  }

  // Clean up
  title = title || path.basename(filePath, path.extname(filePath));
  description = description.filter((d) => d.length > 0);

  return {
    title,
    description:
      description.join(" ").substring(0, 500) || "No description available",
    usage: usageInstructions.join("\n"),
    filename: path.basename(filePath),
    ext: path.extname(filePath).substring(1),
  };
}

/**
 * Generate markdown page for a script
 * @param {string} scriptPath - Path to script file
 * @param {string} category - Category name
 * @param {object} metadata - Extracted metadata
 * @returns {string} Generated markdown content
 */
function generateScriptPage(scriptPath, category, metadata) {
  const code = fs.readFileSync(scriptPath, "utf-8");
  const fileExt = metadata.ext === "sh" ? "bash" : metadata.ext;

  // Escape strings for YAML frontmatter
  const escapeYaml = (str) => {
    // Replace quotes and newlines, then wrap in quotes
    return JSON.stringify(str.replace(/\n/g, " "));
  };

  let markdown = `---
title: ${escapeYaml(metadata.title)}
description: ${escapeYaml(metadata.description)}
---

# ${metadata.title}

${metadata.description}

## Code

\`\`\`${fileExt}
${code}
\`\`\`
`;

  if (metadata.usage) {
    markdown += `
## Usage Instructions

\`\`\`
${metadata.usage}
\`\`\`
`;
  }

  markdown += `
## File Information

- **File**: \`${metadata.filename}\`
- **Category**: ${CATEGORY_INFO[category].title}
- **Language**: ${fileExt.toUpperCase()}

---

[View on GitHub](https://github.com/ropean/scripts/blob/main/${category}/${
    metadata.filename
  })
`;

  return markdown;
}

/**
 * Generate category index page
 * @param {string} category - Category name
 * @param {Array} scripts - List of script metadata
 * @returns {string} Generated markdown content
 */
function generateCategoryIndex(category, scripts) {
  const info = CATEGORY_INFO[category];

  let markdown = `---
title: ${info.title}
---

# ${info.icon} ${info.title}

${info.description}

## Available Scripts

`;

  scripts.forEach((script) => {
    markdown += `### [${script.metadata.title}](./${script.slug})\n\n`;
    markdown += `${script.metadata.description}\n\n`;
    markdown += `**File**: \`${script.metadata.filename}\`\n\n`;
  });

  return markdown;
}

/**
 * Main generation function
 */
function generateDocs() {
  console.log("🚀 Starting documentation generation...\n");

  const sidebarConfig = {};

  CATEGORIES.forEach((category) => {
    console.log(`📁 Processing ${category}...`);

    const categoryDir = path.join(ROOT_DIR, category);
    const docsCategory = path.join(DOCS_DIR, category);

    // Create docs category directory
    if (fs.existsSync(docsCategory)) {
      fs.rmSync(docsCategory, { recursive: true });
    }
    fs.mkdirSync(docsCategory, { recursive: true });

    if (!fs.existsSync(categoryDir)) {
      console.log(`   ⚠️  Directory not found, skipping...`);
      return;
    }

    // Get all script files
    const files = fs
      .readdirSync(categoryDir)
      .filter(
        (f) => f.endsWith(".js") || f.endsWith(".sh") || f.endsWith(".py")
      );

    if (files.length === 0) {
      console.log(`   ℹ️  No scripts found`);
      return;
    }

    const scripts = [];

    // Process each script
    files.forEach((file) => {
      const scriptPath = path.join(categoryDir, file);
      const metadata = extractMetadata(scriptPath);
      const slug = path.basename(file, path.extname(file));

      // Generate markdown page
      const markdown = generateScriptPage(scriptPath, category, metadata);
      const mdPath = path.join(docsCategory, `${slug}.md`);
      fs.writeFileSync(mdPath, markdown);

      scripts.push({ metadata, slug, file });
      console.log(`   ✅ Generated: ${slug}.md`);
    });

    // Generate category index
    const indexMarkdown = generateCategoryIndex(category, scripts);
    fs.writeFileSync(path.join(docsCategory, "index.md"), indexMarkdown);
    console.log(`   ✅ Generated: index.md\n`);

    // Build sidebar config
    sidebarConfig[`/${category}/`] = [
      {
        text: CATEGORY_INFO[category].title,
        items: scripts.map((s) => ({
          text: s.metadata.title,
          link: `/${category}/${s.slug}`,
        })),
      },
    ];
  });

  // Write sidebar config
  writeSidebarConfig(sidebarConfig);

  console.log("✨ Documentation generation complete!\n");
}

/**
 * Write sidebar configuration to JSON file
 * @param {object} sidebarConfig - Generated sidebar configuration
 */
function writeSidebarConfig(sidebarConfig) {
  fs.writeFileSync(SIDEBAR_FILE, JSON.stringify(sidebarConfig, null, 2));
  console.log("📝 Updated sidebar configuration");
}

// Run the generator
try {
  generateDocs();
} catch (error) {
  console.error("❌ Error generating docs:", error);
  process.exit(1);
}
