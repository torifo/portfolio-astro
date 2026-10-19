// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

import react from '@astrojs/react';

import { existsSync, readFileSync } from 'node:fs';

// 旅の URL 名を付け替えたときの旧 → 新（scripts/journey/build_trips.py が書き足す）。旧 URL には新 URL へ飛ぶページを作る。
// 静的ビルドなので 301 ではなく meta refresh のページになる（nginx の 301 は付け替えのたびに設定を手で直すことになるので使わない）。
// 今ある旅と同じ名前の旧名は作らない（旅のページを上書きする）。行き先の旅が無くなった転送も作らない
const readJson = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf-8'));
const liveTrips = new Set(readJson('./data/journey/trips.json').trips.filter((t) => !t.hidden).map((t) => t.slug));
const tripRedirects = Object.entries(
  existsSync(new URL('./data/journey/trip_redirects.json', import.meta.url))
    ? readJson('./data/journey/trip_redirects.json').redirects
    : {}
).filter(([from, to]) => !liveTrips.has(from) && liveTrips.has(to));

// https://astro.build/config
export default defineConfig({
  // OGP の og:image は絶対URLでないとSNS側が解決できない。その基準として置く。
  site: 'https://portorifo.riumu.net',

  // Astro 7 で既定が 'jsx'（行をまたぐ要素の間の空白を消す）に変わった。「hello world」が「helloworld」になるので、
  // Astro 6 までと同じ HTML の空白の扱い（表示を変えない範囲で詰める）にしておく
  compressHTML: true,

  redirects: Object.fromEntries(
    tripRedirects.map(([from, to]) => [`/journey/trips/${from}`, `/journey/trips/${to}/`])
  ),

  vite: {
    plugins: [tailwindcss()]
  },

  integrations: [react()]
});