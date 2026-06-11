// @ts-check
// Copy to: website/docusaurus.config.js
//
// CUSTOMIZE (search for ALL-CAPS placeholders):
//  - PROJECT / amattas / hass-dmp and the tagline
//  - navbar items (keep the version dropdown if you cut doc versions)
//
// Versioning: cutting a release version is part of the release-bump PR:
//   cd website && npm run docusaurus docs:version X.Y.Z
// The latest cut version serves at the site root; main's docs at /dev.
const { themes: prismThemes } = require('prism-react-renderer');

const config = {
  title: 'DMP for Home Assistant',
  tagline: 'DMP alarm panel integration for Home Assistant',
  url: 'https://amattas.github.io',
  baseUrl: '/hass-dmp/',
  organizationName: 'amattas',
  projectName: 'hass-dmp',
  onBrokenLinks: 'throw',
  favicon: 'img/favicon.svg',
  themeConfig: {
    // No defaultMode: follow the visitor's OS/browser preference. (A manual
    // toggle persists in localStorage and overrides this — by design.)
    colorMode: { respectPrefersColorScheme: true },
    // Docusaurus's default prism theme (palenight) is a dark-background token
    // palette in BOTH modes — unreadable on light panels. Per-mode themes:
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.nightOwl,
      additionalLanguages: ['bash', 'python'],
    },
    navbar: {
      title: 'DMP for Home Assistant',
      logo: { src: 'img/logo.svg', width: 26, height: 26 },
      items: [
        { type: 'docsVersionDropdown', position: 'right' },
        {
          href: 'https://github.com/amattas/hass-dmp',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
  },
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          // NOTE: until the FIRST version is cut, `current` is the only docs
          // tree and this block would strand the site root at /dev — either
          // cut a version right away or comment the block out until then.
          versions: {
            current: { label: 'dev (main)', path: 'dev' },
          },
        },
        blog: false,
        theme: { customCss: './src/css/custom.css' },
        sitemap: { lastmod: 'date', changefreq: 'weekly', priority: 0.5, filename: 'sitemap.xml' },
      },
    ],
  ],
  themes: [
    [
      // Self-hosted full-text search — no external service, indexed at build time.
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        docsRouteBasePath: '/',
        indexBlog: false,
        highlightSearchTermsOnTargetPage: true,
      },
    ],
  ],
};
module.exports = config;
