import { writeFile, mkdir, copyFile, access } from "node:fs/promises";
import { dirname } from "node:path";

// Import the VitePress config to read sitemap hostname if present
import config from "../docs/.vitepress/config.mjs";

async function main() {
  try {
    const outDir = "docs/.vitepress/dist";

    // Try to read sitemap hostname from config
    const hostname = config?.sitemap?.hostname || "/";

    const sitemapUrl = hostname.endsWith("/") ? `${hostname}sitemap.xml` : `${hostname}/sitemap.xml`;

    const content = `User-agent: *\nAllow: /\n\nSitemap: ${sitemapUrl}\n`;

    // Ensure output directory exists (it should after build)
    await mkdir(outDir, { recursive: true });

    const target = `${outDir.replace(/\\/g, "/")}/robots.txt`;
    await writeFile(target, content, "utf8");

    console.log(`Wrote robots.txt -> ${target}`);

    // For SPA fallback on some hosts (Cloudflare Pages / Netlify patterns), copy 404.html to 200.html if it exists
    try {
      const src404 = `${outDir.replace(/\\/g, "/")}/404.html`;
      const dst200 = `${outDir.replace(/\\/g, "/")}/200.html`;
      // check if 404 exists
      await access(src404);
      await copyFile(src404, dst200);
      console.log(`Copied 404.html -> 200.html for SPA fallback (${dst200})`);
    } catch (e) {
      // no 404 present or copy failed; not fatal
    }
  } catch (err) {
    console.error("Failed to generate robots.txt:", err);
    process.exitCode = 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith("generate-robots.mjs")) {
  main();
}
