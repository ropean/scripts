#!/usr/bin/env node

/**
 * Test script to verify documentation build output
 * Ensures that routing and metadata are correct
 */

const fs = require("fs");
const path = require("path");

const DOCS_DIR = path.join(__dirname, "..", "docs");
const DIST_DIR = path.join(DOCS_DIR, ".vitepress", "dist");

let passed = 0;
let failed = 0;

/**
 * Test helper function
 */
function test(description, fn) {
  try {
    fn();
    console.log(`✅ PASS: ${description}`);
    passed++;
  } catch (error) {
    console.error(`❌ FAIL: ${description}`);
    console.error(`   ${error.message}`);
    failed++;
  }
}

/**
 * Assert helper
 */
function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

/**
 * Check if file exists
 */
function fileExists(filePath) {
  return fs.existsSync(filePath);
}

/**
 * Read file content
 */
function readFile(filePath) {
  return fs.readFileSync(filePath, "utf-8");
}

/**
 * Decode HTML entities
 */
function decodeHtmlEntities(text) {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

/**
 * Extract metadata from HTML
 */
function extractMetadata(html) {
  const titleMatch = html.match(/<title>([^<]+)<\/title>/);
  const descMatch = html.match(
    /<meta name="description" content="([^"]+)"/
  );

  return {
    title: titleMatch ? decodeHtmlEntities(titleMatch[1]) : null,
    description: descMatch ? decodeHtmlEntities(descMatch[1]) : null,
  };
}

console.log("🧪 Running documentation tests...\n");

// Test 1: Old script-template.md should NOT exist in docs root
test("docs/script-template.md should NOT exist", () => {
  const filePath = path.join(DOCS_DIR, "script-template.md");
  assert(
    !fileExists(filePath),
    "Old script-template.md still exists in docs root"
  );
});

// Test 2: script-template directory should NOT exist in dist
test("dist/script-template directory should NOT exist", () => {
  const dirPath = path.join(DIST_DIR, "script-template");
  assert(
    !fileExists(dirPath),
    "script-template directory exists in dist (should not)"
  );
});

// Test 3: /help/ index should exist and have correct metadata
test("/help/index.html should exist with correct title and description", () => {
  const filePath = path.join(DIST_DIR, "help", "index.html");
  assert(fileExists(filePath), "/help/index.html does not exist");

  const html = readFile(filePath);
  const metadata = extractMetadata(html);

  assert(
    metadata.title === "Help & Documentation | Scripts Collection",
    `Wrong title: ${metadata.title}`
  );
  assert(
    metadata.description ===
      "Guidelines, templates, and documentation for working with this repository",
    `Wrong description: ${metadata.description}`
  );
});

// Test 4: /help/script-template should exist with correct metadata
test("/help/script-template.html should exist with correct metadata", () => {
  const filePath = path.join(DIST_DIR, "help", "script-template.html");
  assert(fileExists(filePath), "/help/script-template.html does not exist");

  const html = readFile(filePath);
  const metadata = extractMetadata(html);

  assert(
    metadata.title === "Script Format Specification | Scripts Collection",
    `Wrong title: ${metadata.title}`
  );
  assert(
    metadata.description ===
      "This document defines the standard format for all scripts in this repository.",
    `Wrong description: ${metadata.description}`
  );
});

// Test 5: /help/navigation-overflow should exist
test("/help/navigation-overflow.html should exist", () => {
  const filePath = path.join(DIST_DIR, "help", "navigation-overflow.html");
  assert(
    fileExists(filePath),
    "/help/navigation-overflow.html does not exist"
  );
});

// Test 6: Check sidebar.json has correct help entries
test("sidebar.json should have /help/ entries", () => {
  const sidebarPath = path.join(DOCS_DIR, ".vitepress", "sidebar.json");
  assert(fileExists(sidebarPath), "sidebar.json does not exist");

  const sidebar = JSON.parse(readFile(sidebarPath));
  assert(sidebar["/help/"], "No /help/ section in sidebar");
  assert(
    sidebar["/help/"][0].items.length === 2,
    "Wrong number of help items in sidebar"
  );

  const scriptTemplateItem = sidebar["/help/"][0].items.find(
    (item) => item.link === "/help/script-template"
  );
  assert(
    scriptTemplateItem,
    "script-template not found in sidebar /help/ items"
  );
  assert(
    scriptTemplateItem.text === "Script Format Specification",
    `Wrong sidebar text: ${scriptTemplateItem.text}`
  );
});

// Test 7: Check nav.json has Help & Documentation entry
test("nav.json should have Help & Documentation entry", () => {
  const navPath = path.join(DOCS_DIR, ".vitepress", "nav.json");
  assert(fileExists(navPath), "nav.json does not exist");

  const nav = JSON.parse(readFile(navPath));
  const helpNav = nav.find((item) => item.link === "/help/");
  assert(helpNav, "No /help/ entry in nav");
  assert(
    helpNav.text === "Help & Documentation",
    `Wrong nav text: ${helpNav.text}`
  );
});

// Test 8: Index page should link to /help/script-template (not /script-template)
test("index.md should link to /help/script-template", () => {
  const indexPath = path.join(DOCS_DIR, "index.md");
  assert(fileExists(indexPath), "index.md does not exist");

  const content = readFile(indexPath);
  assert(
    content.includes("/help/script-template"),
    "index.md does not link to /help/script-template"
  );
  assert(
    !content.includes("](/script-template)") &&
      !content.includes("](/script-template "),
    "index.md still has old /script-template link"
  );
});

// Summary
console.log("\n" + "=".repeat(50));
console.log(`Tests completed: ${passed + failed}`);
console.log(`✅ Passed: ${passed}`);
console.log(`❌ Failed: ${failed}`);
console.log("=".repeat(50));

if (failed > 0) {
  process.exit(1);
}
