import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://example.com', // TODO: set your real domain
  integrations: [sitemap()],
  // If you added aliases earlier:
  // alias: { '@layouts': './src/layouts' },
});

