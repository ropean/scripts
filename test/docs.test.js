/**
 * Test suite for documentation build output
 * Ensures that routing and metadata are correct
 */

const { describe, test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const DOCS_DIR = path.join(__dirname, "..", "docs");
const DIST_DIR = path.join(DOCS_DIR, ".vitepress", "dist");

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
  const descMatch = html.match(/<meta name="description" content="([^"]+)"/);

  return {
    title: titleMatch ? decodeHtmlEntities(titleMatch[1]) : null,
    description: descMatch ? decodeHtmlEntities(descMatch[1]) : null,
  };
}

describe("Documentation Build Tests", () => {
  test("docs/script-template.md should NOT exist", () => {
    const filePath = path.join(DOCS_DIR, "script-template.md");
    assert.strictEqual(
      fileExists(filePath),
      false,
      "Old script-template.md still exists in docs root"
    );
  });

  test("dist/script-template directory should NOT exist", () => {
    const dirPath = path.join(DIST_DIR, "script-template");
    assert.strictEqual(
      fileExists(dirPath),
      false,
      "script-template directory exists in dist (should not)"
    );
  });

  test("/help/index.html should exist with correct title and description", () => {
    const filePath = path.join(DIST_DIR, "help", "index.html");
    assert.ok(fileExists(filePath), "/help/index.html does not exist");

    const html = readFile(filePath);
    const metadata = extractMetadata(html);

    assert.strictEqual(
      metadata.title,
      "Docs | Scripts Collection",
      `Wrong title: ${metadata.title}`
    );
    assert.strictEqual(
      metadata.description,
      "Guidelines, templates, and documentation for working with this repository",
      `Wrong description: ${metadata.description}`
    );
  });

  test("/help/script-template.html should exist with correct metadata", () => {
    const filePath = path.join(DIST_DIR, "help", "script-template.html");
    assert.ok(
      fileExists(filePath),
      "/help/script-template.html does not exist"
    );

    const html = readFile(filePath);
    const metadata = extractMetadata(html);

    assert.strictEqual(
      metadata.title,
      "Script Format Specification | Scripts Collection",
      `Wrong title: ${metadata.title}`
    );
    assert.strictEqual(
      metadata.description,
      "This document defines the standard format for all scripts in this repository.",
      `Wrong description: ${metadata.description}`
    );
  });

  test("/help/navigation-overflow.html should exist", () => {
    const filePath = path.join(DIST_DIR, "help", "navigation-overflow.html");
    assert.ok(
      fileExists(filePath),
      "/help/navigation-overflow.html does not exist"
    );
  });

  test("sidebar.json should have /help/ entries", () => {
    const sidebarPath = path.join(DOCS_DIR, ".vitepress", "sidebar.json");
    assert.ok(fileExists(sidebarPath), "sidebar.json does not exist");

    const sidebar = JSON.parse(readFile(sidebarPath));
    assert.ok(sidebar["/help/"], "No /help/ section in sidebar");
    assert.strictEqual(
      sidebar["/help/"][0].items.length,
      2,
      "Wrong number of help items in sidebar"
    );

    const scriptTemplateItem = sidebar["/help/"][0].items.find(
      (item) => item.link === "/help/script-template"
    );
    assert.ok(
      scriptTemplateItem,
      "script-template not found in sidebar /help/ items"
    );
    assert.strictEqual(
      scriptTemplateItem.text,
      "Script Format Specification",
      `Wrong sidebar text: ${scriptTemplateItem.text}`
    );
  });

  test("nav.json should have Docs entry", () => {
    const navPath = path.join(DOCS_DIR, ".vitepress", "nav.json");
    assert.ok(fileExists(navPath), "nav.json does not exist");

    const nav = JSON.parse(readFile(navPath));
    const helpNav = nav.find((item) => item.link === "/help/");
    assert.ok(helpNav, "No /help/ entry in nav");
    assert.strictEqual(helpNav.text, "Docs", `Wrong nav text: ${helpNav.text}`);
  });

  test("index.md should link to /help/script-template", () => {
    const indexPath = path.join(DOCS_DIR, "index.md");
    assert.ok(fileExists(indexPath), "index.md does not exist");

    const content = readFile(indexPath);
    assert.ok(
      content.includes("/help/script-template"),
      "index.md does not link to /help/script-template"
    );
    assert.ok(
      !content.includes("](/script-template)") &&
        !content.includes("](/script-template "),
      "index.md still has old /script-template link"
    );
  });
});
