import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
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
      social: {
        github: 'https://github.com/IAmJonoBo/Hephaestus',
      },
      editLink: {
        baseUrl: 'https://github.com/IAmJonoBo/Hephaestus/edit/main/docs-site/',
      },
      customCss: [
        './src/styles/custom.css',
      ],
      sidebar: [
        {
          label: 'Start Here',
          items: [
            { label: 'Introduction', link: '/' },
            { label: 'Getting Started', link: '/tutorials/getting-started/' },
          ],
        },
        {
          label: 'Tutorials',
          autogenerate: { directory: 'tutorials' },
        },
        {
          label: 'How-To Guides',
          collapsed: false,
          items: [
            { label: 'Install from Wheelhouse', link: '/how-to/install-wheelhouse/' },
            { label: 'Configure Your Editor', link: '/how-to/editor-setup/' },
            { label: 'Operating Safely', link: '/how-to/operating-safely/' },
            { label: 'Quality Gate Validation', link: '/how-to/quality-gates/' },
            { label: 'CI/CD Setup', link: '/how-to/ci-setup/' },
            { label: 'AI Agent Integration', link: '/how-to/ai-agent-integration/' },
            { label: 'Release Process', link: '/how-to/release-process/' },
            { label: 'Testing Guide', link: '/how-to/testing/' },
            { label: 'E2E Testing', link: '/how-to/e2e-testing/' },
            { label: 'Troubleshooting', link: '/how-to/troubleshooting/' },
            { label: 'Observability', link: '/how-to/observability/' },
            { label: 'Plugin Development', link: '/how-to/plugin-development/' },
            { label: 'Plugin Review Process', link: '/how-to/plugin-review-process/' },
          ],
        },
        {
          label: 'Explanation',
          collapsed: false,
          items: [
            { label: 'Architecture Overview', link: '/explanation/architecture/' },
            { label: 'Lifecycle Playbook', link: '/explanation/lifecycle/' },
            { label: 'Frontier Standards', link: '/explanation/frontier-standards/' },
            { label: 'Red Team Analysis', link: '/explanation/frontier-red-team-gap-analysis/' },
            { label: 'ExFAT Compatibility', link: '/explanation/exfat-compatibility/' },
          ],
        },
        {
          label: 'Reference',
          collapsed: false,
          items: [
            { label: 'CLI Reference', link: '/reference/cli/' },
            { label: 'REST API Reference', link: '/reference/api/' },
            { label: 'Telemetry Events', link: '/reference/telemetry-events/' },
            { label: 'Plugin Catalog', link: '/reference/plugin-catalog/' },
            { label: 'Refactoring Toolkit', link: '/reference/refactoring-toolkit/' },
            { label: 'CLI Autocompletion', link: '/reference/cli-completions/' },
            { label: 'Pre-Release Checklist', link: '/reference/pre-release-checklist/' },
          ],
        },
        {
          label: 'Architecture Decisions',
          collapsed: true,
          autogenerate: { directory: 'adr' },
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
