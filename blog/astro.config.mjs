 import { defineConfig } from 'astro/config';
  import tailwind from '@astrojs/tailwind';
  import mdx from '@astrojs/mdx';
  import sitemap from '@astrojs/sitemap';

  export default defineConfig({
    site: 'https://enjoynews.com.br',
    integrations: [
      tailwind(),
      mdx(),
      sitemap(),
    ],
    markdown: { shikiConfig: { theme: 'github-dark' } },
    vite: { ssr: { noExternal: ['date-fns-tz'] } },
  });