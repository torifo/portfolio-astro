// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  // OGP の og:image は絶対URLでないとSNS側が解決できない。その基準として置く。
  site: 'https://portorifo.riumu.net',

  vite: {
    plugins: [tailwindcss()]
  },

  integrations: [react()]
});