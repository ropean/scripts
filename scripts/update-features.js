#!/usr/bin/env node

/**
 * Update features section in docs/index.md based on category configs
 * Automatically scans script-files directories and generates feature entries
 */

const fs = require("fs");
const path = require("path");

// Configuration
const ROOT_DIR = path.join(__dirname, "..");
const SCRIPT_FILES_DIR = path.join(ROOT_DIR, "script-files");
const DOCS_INDEX = path.join(ROOT_DIR, "docs", "index.md");

/**
 * Load category configuration from config.js
 * @param {string} categoryPath - Path to category directory
 * @param {string} categoryName - Name of the category directory
 * @returns {object} Category configuration with defaults
 */
function loadCategoryConfig(categoryPath, categoryName) {
  const configPath = path.join(categoryPath, "config.js");

  if (fs.existsSync(configPath)) {
    try {
      // Clear require cache to get fresh config
      delete require.cache[require.resolve(configPath)];
      const config = require(configPath);
      return {
        ...config,
        link: `/${categoryName}/`,
      };
    } catch (error) {
      console.warn(`   ⚠️  Failed to load ${categoryName}/config.js: ${error.message}`);
    }
  }

  // Return default config based on directory name
  return {
    title: categoryName.charAt(0).toUpperCase() + categoryName.slice(1),
    description: `Scripts in the ${categoryName} category`,
    icon: "📄",
    order: 999,
    link: `/${categoryName}/`,
  };
}

/**
 * Get all category directories with their configs
 * @returns {Array} List of category configs sorted by order
 */
function getCategoryConfigs() {
  if (!fs.existsSync(SCRIPT_FILES_DIR)) {
    console.error(`❌ Error: ${SCRIPT_FILES_DIR} does not exist`);
    process.exit(1);
  }

  const categories = fs
    .readdirSync(SCRIPT_FILES_DIR)
    .filter((name) => {
      const fullPath = path.join(SCRIPT_FILES_DIR, name);
      return fs.statSync(fullPath).isDirectory();
    })
    .map((name) => {
      const categoryPath = path.join(SCRIPT_FILES_DIR, name);
      return loadCategoryConfig(categoryPath, name);
    })
    .sort((a, b) => (a.order || 999) - (b.order || 999));

  return categories;
}

/**
 * Generate features YAML section from category configs
 * @param {Array} categories - List of category configs
 * @returns {string} Features YAML content
 */
function generateFeaturesYaml(categories) {
  const features = categories.map((cat) => {
    return [
      `  - icon: ${cat.icon}`,
      `    title: ${cat.title}`,
      `    details: ${cat.description}`,
      `    link: ${cat.link}`,
    ].join("\n");
  });

  return `features:\n${features.join("\n")}`;
}

/**
 * Update features section in docs/index.md
 * @param {string} featuresYaml - New features YAML content
 */
function updateIndexFile(featuresYaml) {
  if (!fs.existsSync(DOCS_INDEX)) {
    console.error(`❌ Error: ${DOCS_INDEX} does not exist`);
    process.exit(1);
  }

  const content = fs.readFileSync(DOCS_INDEX, "utf-8");

  // Match the features section (from "features:" to the "---" that ends the frontmatter)
  const featuresRegex = /^features:[\s\S]*?(?=\n---)/m;

  if (!featuresRegex.test(content)) {
    console.error("❌ Error: Could not find features section in index.md");
    process.exit(1);
  }

  const updatedContent = content.replace(featuresRegex, featuresYaml);

  // Write back to file
  fs.writeFileSync(DOCS_INDEX, updatedContent, "utf-8");

  console.log("✅ Successfully updated features in docs/index.md");
}

/**
 * Main function
 */
function main() {
  console.log("🔄 Updating features in docs/index.md...\n");

  // Get category configs
  const categories = getCategoryConfigs();
  console.log(`📂 Found ${categories.length} categories:`);
  categories.forEach((cat) => {
    console.log(`   ${cat.icon} ${cat.title}`);
  });
  console.log();

  // Generate features YAML
  const featuresYaml = generateFeaturesYaml(categories);

  // Update index.md
  updateIndexFile(featuresYaml);
}

// Run if executed directly
if (require.main === module) {
  main();
}

// Export for testing
module.exports = {
  loadCategoryConfig,
  getCategoryConfigs,
  generateFeaturesYaml,
  updateIndexFile,
};
