import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import mdx from '@astrojs/mdx';
import rss from '@astrojs/rss';
import sitemap from '@astrojs/sitemap';

const SITE_URL = 'https://enjoynews.com.br';

export default defineConfig({
  site: SITE_URL,
  integrations: [
    tailwind(),
    mdx(),
    rss(),
    sitemap(),
  ],
  markdown: {
    shikiConfig: {
      theme: 'github-dark',
      wrap: true,
    },
  },
  vite: {
    optimizeDeps: {
      include: ['date-fns', 'date-fns-tz'],
    },
  },
});