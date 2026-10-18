// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

import react from '@astrojs/react';

import { readFileSync } from 'node:fs';

// 旅の URL 名を付け替えたときの旧 → 新（scripts/journey/build_trips.py が書き足す）。旧 URL には新 URL へ飛ぶページを作る。
// 静的ビルドなので 301 ではなく meta refresh のページになる（nginx の 301 は付け替えのたびに設定を手で直すことになるので使わない）
const tripRedirects = JSON.parse(
  readFileSync(new URL('./data/journey/trip_redirects.json', import.meta.url), 'utf-8')
).redirects;

// https://astro.build/config
export default defineConfig({
  // OGP の og:image は絶対URLでないとSNS側が解決できない。その基準として置く。
  site: 'https://portorifo.riumu.net',

  redirects: Object.fromEntries(
    Object.entries(tripRedirects).map(([from, to]) => [`/journey/trips/${from}`, `/journey/trips/${to}/`])
  ),

  vite: {
    plugins: [tailwindcss()]
  },

  integrations: [react()]
});