/**
 * Test suite for update-features.js script
 * Ensures features are correctly generated from category configs
 */

const { describe, test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const { loadCategoryConfig, getCategoryConfigs, generateFeaturesYaml } = require("../scripts/update-features.js");

const ROOT_DIR = path.join(__dirname, "..");
const SCRIPT_FILES_DIR = path.join(ROOT_DIR, "script-files");
const DOCS_INDEX = path.join(ROOT_DIR, "docs", "index.md");

describe("Update Features Script Tests", () => {
  describe("loadCategoryConfig", () => {
    test("should load .config.js from category directory", () => {
      const categoryPath = path.join(SCRIPT_FILES_DIR, "frontend");
      const config = loadCategoryConfig(categoryPath, "frontend");

      assert.ok(config, "Config should be loaded");
      assert.ok(config.title, "Config should have title");
      assert.ok(config.description, "Config should have description");
      assert.ok(config.icon, "Config should have icon");
      assert.strictEqual(config.link, "/frontend/", "Config should have correct link");
    });

    test("should return default config if .config.js doesn't exist", () => {
      const tempDir = fs.mkdtempSync(path.join(__dirname, "temp-"));
      const config = loadCategoryConfig(tempDir, "testcategory");

      assert.strictEqual(config.title, "Testcategory", "Should have capitalized title");
      assert.ok(config.description, "Should have default description");
      assert.strictEqual(config.icon, "📄", "Should have default icon");
      assert.strictEqual(config.link, "/testcategory/", "Should have correct link");

      // Cleanup
      fs.rmdirSync(tempDir);
    });
  });

  describe("getCategoryConfigs", () => {
    test("should return array of category configs", () => {
      const categories = getCategoryConfigs();

      assert.ok(Array.isArray(categories), "Should return an array");
      assert.ok(categories.length > 0, "Should have at least one category");

      // Verify each category has required properties
      categories.forEach((cat) => {
        assert.ok(cat.title, "Category should have title");
        assert.ok(cat.description, "Category should have description");
        assert.ok(cat.icon, "Category should have icon");
        assert.ok(cat.link, "Category should have link");
      });
    });

    test("should sort categories by order field", () => {
      const categories = getCategoryConfigs();

      // Check if categories are sorted
      for (let i = 0; i < categories.length - 1; i++) {
        const currentOrder = categories[i].order || 999;
        const nextOrder = categories[i + 1].order || 999;
        assert.ok(
          currentOrder <= nextOrder,
          `Categories should be sorted by order: ${categories[i].title} (${currentOrder}) should come before ${
            categories[i + 1].title
          } (${nextOrder})`
        );
      }
    });
  });

  describe("generateFeaturesYaml", () => {
    test("should generate valid YAML from category configs", () => {
      const mockCategories = [
        {
          title: "Test Category",
          description: "Test description",
          icon: "🧪",
          link: "/test/",
        },
      ];

      const yaml = generateFeaturesYaml(mockCategories);

      assert.ok(yaml.startsWith("features:"), "YAML should start with 'features:'");
      assert.ok(yaml.includes("icon: 🧪"), "YAML should include icon");
      assert.ok(yaml.includes("title: Test Category"), "YAML should include title");
      assert.ok(yaml.includes("details: Test description"), "YAML should include description");
      assert.ok(yaml.includes("link: /test/"), "YAML should include link");
    });

    test("should handle multiple categories", () => {
      const mockCategories = [
        {
          title: "Category 1",
          description: "Description 1",
          icon: "📁",
          link: "/cat1/",
        },
        {
          title: "Category 2",
          description: "Description 2",
          icon: "📂",
          link: "/cat2/",
        },
      ];

      const yaml = generateFeaturesYaml(mockCategories);

      assert.ok(yaml.includes("Category 1"), "Should include first category");
      assert.ok(yaml.includes("Category 2"), "Should include second category");
      assert.ok(yaml.includes("📁"), "Should include first icon");
      assert.ok(yaml.includes("📂"), "Should include second icon");
    });
  });

  describe("Integration tests", () => {
    test("generated YAML should match actual categories", () => {
      const categories = getCategoryConfigs();
      const yaml = generateFeaturesYaml(categories);

      // Verify all categories are in the YAML
      categories.forEach((cat) => {
        assert.ok(yaml.includes(cat.title), `YAML should include category: ${cat.title}`);
        assert.ok(yaml.includes(cat.icon), `YAML should include icon: ${cat.icon}`);
      });
    });

    test("docs/index.md should have features section", () => {
      assert.ok(fs.existsSync(DOCS_INDEX), "docs/index.md should exist");

      const content = fs.readFileSync(DOCS_INDEX, "utf-8");
      assert.ok(content.includes("features:"), "index.md should have features section");
    });
  });
});
