#!/usr/bin/env node
/**
 * microCMS の内容を data/microcms/*.json へ取り込む。
 *
 * ビルドから取得を切り離すためのもの。以前は Astro のビルド中に microCMS を
 * 叩いており、TLS 接続が一瞬切れただけでデプロイが丸ごと落ちたことがある
 * （read ECONNRESET・全ページ生成後の最後の1本で失敗）。
 *
 * 取得に失敗したファイルは**書き換えない**。リポジトリにコミット済みの前回分が
 * そのまま残り、サイトは最後に取れた内容で出る。空にもならず、デプロイも止まらない。
 *
 *   PUBLIC_MICROCMS_API_KEY / PUBLIC_MICROCMS_SERVICE_DOMAIN を環境変数か
 *   .env から読む。
 *
 * リポジトリには空の種ファイル（_placeholder: true）を置いてある。鍵を持たない
 * 手元でもビルドが通るようにするためで、CI が本物で上書きする。取得に失敗して
 * 残っているのが種ファイルだけなら、中身の無いサイトを本番へ出さないよう終了コード1で
 * ビルドを止める。
 *
 * 終了コード: 実データのキャッシュが無いまま取得に失敗したときだけ 1。
 */
import { mkdir, readFile, writeFile, access } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT_DIR = join(ROOT, 'data', 'microcms');

const ENDPOINTS = [
  { name: 'profile', path: 'profile' },
  { name: 'opus', path: 'opus?limit=100&orders=createdAt' },
  { name: 'skills', path: 'skills?limit=100' },
  { name: 'games', path: 'games?limit=100' },
];

const ATTEMPTS = 3;
const BASE_WAIT_MS = 600;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function loadEnv() {
  // CI では環境変数、手元では .env を読む
  if (process.env.PUBLIC_MICROCMS_API_KEY && process.env.PUBLIC_MICROCMS_SERVICE_DOMAIN) return;
  try {
    const text = await readFile(join(ROOT, '.env'), 'utf8');
    for (const line of text.split('\n')) {
      const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (match && !process.env[match[1]]) {
        process.env[match[1]] = match[2].replace(/^["']|["']$/g, '');
      }
    }
  } catch {
    // .env が無くてもよい（環境変数だけで動く場合がある）
  }
}

async function fetchOne(path) {
  const key = process.env.PUBLIC_MICROCMS_API_KEY;
  const domain = process.env.PUBLIC_MICROCMS_SERVICE_DOMAIN;
  let lastError;

  for (let attempt = 1; attempt <= ATTEMPTS; attempt += 1) {
    try {
      const response = await fetch(`${domain}${path}`, {
        headers: { 'X-MICROCMS-API-KEY': key },
      });
      if (response.ok) return await response.json();
      // 4xx は鍵やパスの誤りなので待っても直らない
      if (response.status >= 400 && response.status < 500 && response.status !== 429) {
        throw new Error(`HTTP ${response.status}`);
      }
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
      if (String(error.message).startsWith('HTTP 4')) break;
    }
    if (attempt < ATTEMPTS) await sleep(BASE_WAIT_MS * attempt);
  }
  throw lastError;
}

/** 既にあるファイルが「実データ」か「空の種」かを見る。 */
async function cacheState(file) {
  try {
    const data = JSON.parse(await readFile(file, 'utf8'));
    return data && data._placeholder ? 'placeholder' : 'real';
  } catch {
    return 'none';
  }
}

async function main() {
  await loadEnv();
  await mkdir(OUT_DIR, { recursive: true });

  let fetched = 0;
  let cached = 0;
  let missing = 0;

  for (const { name, path } of ENDPOINTS) {
    const file = join(OUT_DIR, `${name}.json`);
    try {
      const data = await fetchOne(path);
      await writeFile(file, `${JSON.stringify(data, null, 1)}\n`, 'utf8');
      fetched += 1;
      console.log(`  取得  ${name}`);
    } catch (error) {
      const state = await cacheState(file);
      if (state === 'real') {
        cached += 1;
        console.warn(`  据置  ${name}: ${error.message} — コミット済みの前回分を使う`);
      } else {
        missing += 1;
        console.error(`  失敗  ${name}: ${error.message} — 実データのキャッシュが無い`);
      }
    }
  }

  console.log(`\n取得 ${fetched} / 前回分を据置 ${cached} / 実データ無し ${missing}`);
  if (missing > 0) {
    console.error('実データが無いまま取得に失敗した。中身の空いたサイトを出さないよう、ここで止める。');
    process.exit(1);
  }
}

main();
