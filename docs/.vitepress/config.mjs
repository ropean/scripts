import { defineConfig } from 'vitepress'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const sidebar = JSON.parse(readFileSync(join(__dirname, 'sidebar.json'), 'utf-8'))

export default defineConfig({
  title: 'Scripts Collection',
  description: 'A curated collection of excellent JavaScript code examples',
  base: '/scripts/',

  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Frontend', link: '/frontend/' },
      { text: 'Backend', link: '/backend/' },
      { text: 'Git', link: '/git/' },
      { text: 'Node', link: '/node/' }
    ],

    sidebar: sidebar,

    socialLinks: [
      { icon: 'github', link: 'https://github.com/ropean/scripts' }
    ],

    search: {
      provider: 'local'
    },

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Sharing excellence in JavaScript, one commit at a time.'
    }
  }
})
