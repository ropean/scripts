#!/usr/bin/env node

/**
 * Auto-generate VitePress documentation from script files
 * Dynamically scans all directories and creates markdown pages
 */

const fs = require("fs");
const path = require("path");

// Configuration
const ROOT_DIR = path.join(__dirname, "..");
const SCRIPT_FILES_DIR = path.join(ROOT_DIR, "script-files");
const MD_FILES_DIR = path.join(ROOT_DIR, "md-files");
const DOCS_DIR = path.join(ROOT_DIR, "docs");
const SIDEBAR_FILE = path.join(DOCS_DIR, ".vitepress", "sidebar.json");

// Directories to exclude from scanning
const EXCLUDED_DIRS = [];

// Supported script file extensions
const SUPPORTED_EXTENSIONS = [
  ".js",
  ".sh",
  ".py",
  ".ts",
  ".mjs",
  ".cjs",
  ".bash",
];

/**
 * Get all category directories (excludes system directories)
 * @returns {Array} List of category directory names
 */
function getCategoryDirectories() {
  return fs
    .readdirSync(SCRIPT_FILES_DIR)
    .filter((name) => {
      const fullPath = path.join(SCRIPT_FILES_DIR, name);
      return (
        fs.statSync(fullPath).isDirectory() && !EXCLUDED_DIRS.includes(name)
      );
    })
    .sort();
}

/**
 * Load category configuration from config.js
 * @param {string} categoryPath - Path to category directory
 * @returns {object} Category configuration
 */
function loadCategoryConfig(categoryPath) {
  const configPath = path.join(categoryPath, "config.js");

  if (fs.existsSync(configPath)) {
    try {
      // Clear require cache to get fresh config
      delete require.cache[require.resolve(configPath)];
      return require(configPath);
    } catch (error) {
      console.warn(`   ⚠️  Failed to load config.js: ${error.message}`);
    }
  }

  // Return default config based on directory name
  const dirName = path.basename(categoryPath);
  return {
    title: dirName.charAt(0).toUpperCase() + dirName.slice(1) + " Scripts",
    description: `Scripts in the ${dirName} category`,
    icon: "📄",
  };
}

/**
 * Extract metadata from script file using @tag format
 * @param {string} filePath - Path to the script file
 * @returns {object} Metadata object with title, description, etc.
 */
function extractMetadata(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const lines = content.split("\n");
  const ext = path.extname(filePath);

  let metadata = {
    title: "",
    description: "",
    author: "",
    version: "",
    example: "",
    requires: "",
    see: "",
    note: "",
  };

  let inHeaderBlock = false;
  let headerLines = [];

  // Extract header block
  for (let i = 0; i < Math.min(100, lines.length); i++) {
    const line = lines[i].trim();

    // Skip shebang lines
    if (line.startsWith("#!")) {
      continue;
    }

    // Detect start of header block
    if (
      !inHeaderBlock &&
      (line.startsWith("/**") || line.startsWith('"""') || line.startsWith("#"))
    ) {
      inHeaderBlock = true;
      headerLines.push(line);
      continue;
    }

    // In header block
    if (inHeaderBlock) {
      headerLines.push(line);

      // Detect end of header block
      if (
        line.includes("*/") ||
        line.includes('"""') ||
        (!line.startsWith("#") && !line.startsWith("*") && line.length > 0)
      ) {
        break;
      }
    }
  }

  // Parse header lines for @tags
  for (const line of headerLines) {
    // Remove comment markers
    let cleanLine = line
      .replace(/^(\/\*\*|\/\/|#|\/?\*+|""")\s*/, "")
      .replace(/\*\/$/, "")
      .replace(/"""\s*$/, "")
      .trim();

    // Parse @tags
    if (cleanLine.startsWith("@title")) {
      metadata.title = cleanLine.replace("@title", "").trim();
    } else if (cleanLine.startsWith("@description")) {
      metadata.description = cleanLine.replace("@description", "").trim();
    } else if (cleanLine.startsWith("@author")) {
      metadata.author = cleanLine.replace("@author", "").trim();
    } else if (cleanLine.startsWith("@version")) {
      metadata.version = cleanLine.replace("@version", "").trim();
    } else if (cleanLine.startsWith("@example")) {
      metadata.example = cleanLine.replace("@example", "").trim();
    } else if (cleanLine.startsWith("@requires")) {
      metadata.requires = cleanLine.replace("@requires", "").trim();
    } else if (cleanLine.startsWith("@see")) {
      metadata.see = cleanLine.replace("@see", "").trim();
    } else if (cleanLine.startsWith("@note")) {
      metadata.note = cleanLine.replace("@note", "").trim();
    } else if (
      !metadata.description &&
      cleanLine &&
      !cleanLine.startsWith("@")
    ) {
      // Fallback: use first non-tag line as description
      if (!metadata.title) {
        metadata.title = cleanLine;
      } else if (cleanLine.length > 10) {
        metadata.description = cleanLine;
      }
    }
  }

  // Fallback to filename if no title found
  if (!metadata.title) {
    metadata.title = path.basename(filePath, ext);
  }

  // Ensure description exists
  if (!metadata.description) {
    metadata.description = "No description available";
  }

  metadata.filename = path.basename(filePath);
  metadata.ext = ext.substring(1);

  return metadata;
}

/**
 * Determine syntax highlighting language for file extension
 * @param {string} ext - File extension (without dot)
 * @returns {string} Language identifier for syntax highlighting
 */
function getLanguage(ext) {
  const languageMap = {
    js: "javascript",
    mjs: "javascript",
    cjs: "javascript",
    ts: "typescript",
    sh: "bash",
    bash: "bash",
    py: "python",
  };
  return languageMap[ext] || ext;
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
  const language = getLanguage(metadata.ext);

  // Escape strings for YAML frontmatter
  const escapeYaml = (str) => {
    return JSON.stringify(str.replace(/\n/g, " "));
  };

  let markdown = `---
title: ${escapeYaml(metadata.title)}
description: ${escapeYaml(metadata.description)}
---

# ${metadata.title}

${metadata.description}

`;

  // Add metadata section
  if (metadata.author || metadata.version || metadata.requires) {
    markdown += `## Metadata\n\n`;
    if (metadata.author) markdown += `- **Author**: ${metadata.author}\n`;
    if (metadata.version) markdown += `- **Version**: ${metadata.version}\n`;
    if (metadata.requires)
      markdown += `- **Dependencies**: ${metadata.requires}\n`;
    if (metadata.see) markdown += `- **See Also**: ${metadata.see}\n`;
    markdown += `\n`;
  }

  // Add note if present
  if (metadata.note) {
    markdown += `:::warning ${metadata.note}\n:::\n\n`;
  }

  // Add code section
  markdown += `## Code\n\n\`\`\`${language}\n${code}\n\`\`\`\n`;

  // Add example if present
  if (metadata.example) {
    markdown += `\n## Example\n\n\`\`\`${language}\n${metadata.example}\n\`\`\`\n`;
  }

  // Add file information
  markdown += `
## File Information

- **Filename**: \`${metadata.filename}\`
- **Category**: ${category}
- **Language**: ${language.toUpperCase()}

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
 * @param {object} categoryInfo - Category configuration
 * @param {Array} scripts - List of script metadata
 * @returns {string} Generated markdown content
 */
function generateCategoryIndex(category, categoryInfo, scripts) {
  let markdown = `---
title: ${categoryInfo.title}
---

# ${categoryInfo.icon} ${categoryInfo.title}

${categoryInfo.description}

## Available Scripts (${scripts.length})

`;

  scripts.forEach((script) => {
    markdown += `### [${script.metadata.title}](./${script.slug})\n\n`;
    markdown += `${script.metadata.description}\n\n`;
    if (script.metadata.author) {
      markdown += `*By ${script.metadata.author}*\n\n`;
    }
    markdown += `**File**: \`${script.metadata.filename}\`\n\n`;
  });

  return markdown;
}

/**
 * Get all MD category directories
 * @returns {Array} List of MD category directory names
 */
function getMdCategoryDirectories() {
  if (!fs.existsSync(MD_FILES_DIR)) {
    return [];
  }

  return fs
    .readdirSync(MD_FILES_DIR)
    .filter((name) => {
      const fullPath = path.join(MD_FILES_DIR, name);
      return (
        fs.statSync(fullPath).isDirectory() && !EXCLUDED_DIRS.includes(name)
      );
    })
    .sort();
}

/**
 * Extract metadata from markdown frontmatter
 * @param {string} filePath - Path to markdown file
 * @returns {object} Metadata with title and description
 */
function extractMarkdownMetadata(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const lines = content.split("\n");

  const metadata = {
    title: "",
    description: "",
  };

  // Check for frontmatter
  if (lines[0] === "---") {
    let inFrontmatter = true;
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      if (line === "---") {
        break;
      }

      // Parse YAML-like frontmatter
      if (line.startsWith("title:")) {
        metadata.title = line.replace("title:", "").trim().replace(/['"]/g, "");
      } else if (line.startsWith("description:")) {
        metadata.description = line.replace("description:", "").trim().replace(/['"]/g, "");
      }
    }
  }

  // Fallback to filename if no title
  if (!metadata.title) {
    metadata.title = path.basename(filePath, ".md");
  }

  return metadata;
}

/**
 * Process markdown files in md-files directory
 * @returns {object} Sidebar configuration for MD categories
 */
function processMdFiles() {
  const mdCategories = getMdCategoryDirectories();
  const mdSidebarConfig = {};
  const mdNavItems = [];

  if (mdCategories.length === 0) {
    console.log("📝 No MD categories found\n");
    return { sidebarConfig: mdSidebarConfig, navItems: mdNavItems };
  }

  console.log("📝 Processing MD files...\n");

  mdCategories.forEach((category) => {
    console.log(`📚 Processing ${category}...`);

    const categoryDir = path.join(MD_FILES_DIR, category);
    const docsCategory = path.join(DOCS_DIR, category);

    // Load category config
    const categoryInfo = loadCategoryConfig(categoryDir);

    // Create docs category directory
    if (!fs.existsSync(docsCategory)) {
      fs.mkdirSync(docsCategory, { recursive: true });
    }

    // Get all markdown files in the category
    const files = fs
      .readdirSync(categoryDir)
      .filter((f) => f.endsWith(".md") && f !== "README.md");

    if (files.length === 0) {
      console.log(`   ℹ️  No markdown files found`);
      return;
    }

    const mdFiles = [];

    // Copy and process each markdown file
    files.forEach((file) => {
      const sourcePath = path.join(categoryDir, file);
      const destPath = path.join(docsCategory, file);
      const slug = path.basename(file, ".md");

      // Copy the file
      fs.copyFileSync(sourcePath, destPath);

      // Extract metadata for sidebar
      const metadata = extractMarkdownMetadata(sourcePath);

      mdFiles.push({
        text: metadata.title,
        link: `/${category}/${slug}`,
      });

      console.log(`   ✅ Copied: ${file}`);
    });

    // Generate category index
    const indexContent = generateMdCategoryIndex(category, categoryInfo, files);
    fs.writeFileSync(path.join(docsCategory, "index.md"), indexContent);
    console.log(`   ✅ Generated: index.md\n`);

    // Build sidebar config for this MD category
    mdSidebarConfig[`/${category}/`] = [
      {
        text: categoryInfo.title,
        items: mdFiles,
      },
    ];

    // Add to navigation
    mdNavItems.push({
      text: categoryInfo.title,
      link: `/${category}/`,
      order: categoryInfo.order || 999,
    });
  });

  return { sidebarConfig: mdSidebarConfig, navItems: mdNavItems };
}

/**
 * Generate category index page for MD files
 * @param {string} category - Category name
 * @param {object} categoryInfo - Category configuration
 * @param {Array} files - List of markdown files
 * @returns {string} Generated markdown content
 */
function generateMdCategoryIndex(category, categoryInfo, files) {
  // Escape strings for YAML frontmatter
  const escapeYaml = (str) => {
    return JSON.stringify(str.replace(/\n/g, " "));
  };

  let markdown = `---
title: ${escapeYaml(categoryInfo.title)}
description: ${escapeYaml(categoryInfo.description)}
---

# ${categoryInfo.icon} ${categoryInfo.title}

${categoryInfo.description}

## Available Documents (${files.length})

`;

  files.forEach((file) => {
    const slug = path.basename(file, ".md");
    const sourcePath = path.join(MD_FILES_DIR, category, file);
    const metadata = extractMarkdownMetadata(sourcePath);

    markdown += `### [${metadata.title}](./${slug})\n\n`;
    if (metadata.description) {
      markdown += `${metadata.description}\n\n`;
    }
  });

  return markdown;
}

/**
 * Main generation function
 */
function generateDocs() {
  console.log("🚀 Starting documentation generation...\n");

  const categories = getCategoryDirectories();
  const sidebarConfig = {};

  if (categories.length === 0) {
    console.log("⚠️  No categories found!");
    return;
  }

  categories.forEach((category) => {
    console.log(`📁 Processing ${category}...`);

    const categoryDir = path.join(SCRIPT_FILES_DIR, category);
    const docsCategory = path.join(DOCS_DIR, category);

    // Load category config
    const categoryInfo = loadCategoryConfig(categoryDir);

    // Create docs category directory
    if (fs.existsSync(docsCategory)) {
      fs.rmSync(docsCategory, { recursive: true });
    }
    fs.mkdirSync(docsCategory, { recursive: true });

    // Get all script files
    const files = fs.readdirSync(categoryDir).filter((f) => {
      const ext = path.extname(f);
      return SUPPORTED_EXTENSIONS.includes(ext) && f !== "config.js";
    });

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
    const indexMarkdown = generateCategoryIndex(
      category,
      categoryInfo,
      scripts
    );
    fs.writeFileSync(path.join(docsCategory, "index.md"), indexMarkdown);
    console.log(`   ✅ Generated: index.md\n`);

    // Build sidebar config
    sidebarConfig[`/${category}/`] = [
      {
        text: categoryInfo.title,
        items: scripts.map((s) => ({
          text: s.metadata.title,
          link: `/${category}/${s.slug}`,
        })),
      },
    ];
  });

  // Process MD files
  const { sidebarConfig: mdSidebarConfig, navItems: mdNavItems } = processMdFiles();

  // Merge sidebar configs (script-files first, then md-files)
  const mergedSidebarConfig = { ...sidebarConfig, ...mdSidebarConfig };

  // Write sidebar config
  writeSidebarConfig(mergedSidebarConfig);

  // Update navigation (script-files first, then md-files)
  updateNavigation(categories, mdNavItems);

  console.log("✨ Documentation generation complete!\n");
  console.log(`📊 Summary:`);
  console.log(`   - Script categories: ${categories.length}`);
  console.log(`   - MD categories: ${mdNavItems.length}`);
  console.log(
    `   - Total scripts: ${Object.values(sidebarConfig).reduce(
      (sum, cat) => sum + cat[0].items.length,
      0
    )}`
  );
  console.log(
    `   - Total MD files: ${Object.values(mdSidebarConfig).reduce(
      (sum, cat) => sum + cat[0].items.length,
      0
    )}`
  );
}

/**
 * Write sidebar configuration to JSON file
 * @param {object} sidebarConfig - Generated sidebar configuration
 */
function writeSidebarConfig(sidebarConfig) {
  fs.writeFileSync(SIDEBAR_FILE, JSON.stringify(sidebarConfig, null, 2));
  console.log("📝 Updated sidebar configuration");
}

/**
 * Update navigation in config file
 * @param {Array} categories - List of script category names
 * @param {Array} mdNavItems - List of MD navigation items
 */
function updateNavigation(categories, mdNavItems = []) {
  const navConfigPath = path.join(DOCS_DIR, ".vitepress", "nav.json");

  // Build script categories navigation
  const scriptNavItems = categories.map((cat) => {
    const categoryPath = path.join(SCRIPT_FILES_DIR, cat);
    const config = loadCategoryConfig(categoryPath);
    return {
      text: config.title,
      link: `/${cat}/`,
      order: config.order || 0,
    };
  });

  // Combine and sort by order
  const allNavItems = [...scriptNavItems, ...mdNavItems].sort(
    (a, b) => (a.order || 0) - (b.order || 0)
  );

  // Determine navigation structure based on number of items
  let navItems;

  if (allNavItems.length <= 6) {
    // Simple flat navigation for small number of items
    navItems = [
      { text: "Home", link: "/" },
      ...allNavItems.map(({ text, link }) => ({ text, link })),
    ];
  } else {
    // Grouped navigation for many items
    navItems = [
      { text: "Home", link: "/" },
      {
        text: "Scripts",
        items: scriptNavItems.map(({ text, link }) => ({ text, link })),
      },
      {
        text: "Documentation",
        items: mdNavItems.map(({ text, link }) => ({ text, link })),
      },
    ];
  }

  fs.writeFileSync(navConfigPath, JSON.stringify(navItems, null, 2));
  console.log("📝 Updated navigation configuration");
  console.log(`   Navigation style: ${allNavItems.length <= 6 ? "flat" : "grouped"}`);
}

// Run the generator
try {
  generateDocs();
} catch (error) {
  console.error("❌ Error generating docs:", error);
  process.exit(1);
}
