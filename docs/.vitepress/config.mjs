import { defineConfig } from "vitepress";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Load dynamically generated sidebar and nav
const sidebar = JSON.parse(
  readFileSync(join(__dirname, "sidebar.json"), "utf-8")
);
const nav = JSON.parse(
  readFileSync(join(__dirname, "nav.json"), "utf-8")
);

export default defineConfig({
  title: "Scripts Collection",
  description: "A curated collection of excellent JavaScript code examples",
  base: "/",

  lang: 'en-US',
  lastUpdated: true,
  cleanUrls: true,
  ignoreDeadLinks: [
    // Ignore localhost links in examples
    /^https?:\/\/localhost/,
  ],

  head: [
    ['link', { rel: 'icon', href: '/logo.svg' }],
    ['link', { rel: 'apple-touch-icon', href: '/logo.svg' }],
    ['meta', { name: 'theme-color', content: '#3eaf7c' }],
    ['meta', { name: 'keywords', content: 'javascript, scripts, code examples, frontend, backend, git, node.js, development, programming' }],
    ['meta', { property: 'og:title', content: 'Scripts Collection - Curated JavaScript Code Examples' }],
    ['meta', { property: 'og:description', content: 'A curated collection of excellent JavaScript code examples for frontend, backend, git automation, and Node.js development' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:url', content: 'https://ropean.github.io/scripts/' }],
    ['meta', { name: 'twitter:card', content: 'summary' }],
    ['meta', { name: 'twitter:title', content: 'Scripts Collection' }],
    ['meta', { name: 'twitter:description', content: 'A curated collection of excellent JavaScript code examples' }]
  ],

  // Build optimizations
  vite: {
    build: {
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true
        }
      },
      chunkSizeWarningLimit: 1000,
      cssCodeSplit: true
    }
  },

  // Sitemap for SEO
  sitemap: {
    hostname: 'https://ropean.github.io/scripts/'
  },

  themeConfig: {
    logo: '/logo.svg',
    nav: nav,
    sidebar: sidebar,

    socialLinks: [
      { icon: "github", link: "https://github.com/ropean/scripts" },
    ],

    search: {
      provider: "local",
    },

    footer: {
      message: "Released under the MIT License.",
      copyright:
        'Built with <a href="https://vitepress.dev/">VitePress</a> by <a href="https://ropean.org/">ropean</a> © 2025',
    },
  },
});
