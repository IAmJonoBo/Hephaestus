import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
  output: 'static',
  site: 'https://iamjonobo.github.io',
  base: '/Hephaestus',
  integrations: [
    starlight({
      title: 'Hephaestus Toolkit',
      description: 'Frontier-grade developer experience toolkit for Python refactoring and quality automation',
      logo: {
        src: './src/assets/logo.svg',
        replacesTitle: false,
      },
      social: [
        {
          label: 'GitHub',
          icon: 'github',
          href: 'https://github.com/IAmJonoBo/Hephaestus',
        },
      ],
      editLink: {
        baseUrl: 'https://github.com/IAmJonoBo/Hephaestus/edit/main/docs-site/',
      },
      customCss: [
        './src/styles/custom.css',
      ],
      sidebar: [
        {
          label: 'Documentation',
          autogenerate: { directory: '/' },
        },
      ],
      components: {
        // Add custom components here if needed
      },
      head: [
        {
          tag: 'meta',
          attrs: {
            property: 'og:image',
            content: 'https://iamjonobo.github.io/Hephaestus/og-image.png',
          },
        },
      ],
      lastUpdated: true,
      pagination: true,
      tableOfContents: {
        minHeadingLevel: 2,
        maxHeadingLevel: 4,
      },
    }),
  ],
  markdown: {
    shikiConfig: {
      theme: 'github-dark',
    },
  },
});
