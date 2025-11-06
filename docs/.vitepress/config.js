import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Scripts Collection',
  description: 'A curated collection of excellent JavaScript code examples',
  base: '/scripts/',

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: 'Home', link: '/' },
      { text: 'Frontend', link: '/frontend/' },
      { text: 'Backend', link: '/backend/' },
      { text: 'Git', link: '/git/' },
      { text: 'Node', link: '/node/' }
    ],

    sidebar: {
          /frontend/: [
                {
                      text: "Frontend Scripts",
                      items: [
                            {
                                  text: "Intercept Decap CMS authentication requests",
                                  link: "/frontend/intercept-requests"
                            },
                            {
                                  text: "React Select Auto Selector",
                                  link: "/frontend/react-select-auto-selector"
                            }
                      ]
                }
          ],
          /backend/: [
                {
                      text: "Backend Scripts",
                      items: [
                            {
                                  text: "local-proxy.js",
                                  link: "/backend/local-proxy"
                            }
                      ]
                }
          ],
          /git/: [
                {
                      text: "Git Tools",
                      items: [
                            {
                                  text: ")",
                                  link: "/git/git-lfs-config-generator"
                            },
                            {
                                  text: ")",
                                  link: "/git/git-submodules"
                            }
                      ]
                }
          ],
          /node/: [
                {
                      text: "Node Utilities",
                      items: [
                            {
                                  text: "Cloudflare Workers Environment Setup Script",
                                  link: "/node/cloudflare-setup"
                            }
                      ]
                }
          ]
    }
      ],
      '/backend/': [
        {
          text: 'Backend Scripts',
          items: [] // Will be auto-generated
        }
      ],
      '/git/': [
        {
          text: 'Git Scripts',
          items: [] // Will be auto-generated
        }
      ],
      '/node/': [
        {
          text: 'Node Scripts',
          items: [] // Will be auto-generated
        }
      ]
    },

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
