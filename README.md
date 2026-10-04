# Toriforium Portfolio

<!-- tech-stack:start (auto-generated) -->
<p align="center">
  <img src="https://img.shields.io/badge/Astro-BC52EE?style=for-the-badge&logo=astro&logoColor=white" alt="Astro">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS">
</p>
<!-- tech-stack:end -->

## 日本語

### 📖 概要

AstroとTypeScriptを使用して構築されたモダンなポートフォリオWebサイトです。microCMS APIによる動的コンテンツ管理、日の出・日没APIによる自動テーマ切り替え、Astro SSG による高速な静的サイト生成を特徴としています。ビルド環境とデプロイ環境を分離し、リソースに配慮した設計で開発しています。

### 🛠️ 使用技術

- **フレームワーク**: Astro (SSG) - 静的サイト生成による高速配信
- **スタイリング**: Tailwind CSS - ユーティリティファーストのCSS
- **言語**: TypeScript - 型安全性とコード品質の向上
- **CMS**: microCMS - ヘッドレスCMSによるコンテンツ管理（Profile・Opus・Skills・Games API）
- **外部API**: Sunrise Sunset API - 日の出・日没時刻による自動テーマ切り替え
- **コンテナ化**: Docker (multi-stage build: node:alpine → nginx:alpine)
- **Webサーバー**: Nginx - 高速な静的ファイル配信
- **レジストリ**: GitHub Container Registry (GHCR)

### ✨ 特徴

- **レスポンシブデザイン**: モバイルからデスクトップまで対応
- **高速パフォーマンス**: Astro SSG による最適化された静的サイト
- **モダンUI**: グラデーションエフェクトとアニメーション
- **動的コンテンツ**: microCMS APIによるビルド時データ取得（Profile・Opus・Skills・Games）
- **動的ルーティング**: `getStaticPaths()` による Opus 詳細ページ自動生成
- **カテゴリ/タグフィルター**: OpusSection・AboutSection でのクライアント側絞り込み
- **スキルタグ連携**: Opusの各サービスにスキルタグを表示、クリックでSkillsセクションへスムーズスクロール
- **スキル自動ソート**: レベル降順・作成日昇順でカテゴリ内を自動整列（固定カテゴリ順）
- **自動テーマ切り替え**: 日の出・日没時刻に基づくライト/ダークモード（JSTキャッシュ管理）
- **リアルタイム時計**: ヘッダーにJST時刻をリアルタイム表示
- **ビルド時刻表示**: フッターにビルド日時を自動埋め込み（JST）
- **Journey（Instagram 連携）**: 旅の写真を都道府県・旅・聖地巡礼・テーマの4つの軸で閲覧。新着は毎日 GitHub Actions が取り込んで PR にし、本文の日付の後ろに場所を書いた投稿は自動でマージする

### 📁 プロジェクト構造

```
/
├── src/
│   ├── components/
│   │   ├── Header.astro          # ヘッダーナビゲーション
│   │   ├── ThemeToggle.astro     # テーマ切り替え・時刻表示（JSTキャッシュ）
│   │   ├── Footer.astro          # フッター（ビルド時刻自動表示）
│   │   ├── DetailHeader.astro    # Opus詳細ページ用ヘッダー
│   │   ├── GameSNS.astro         # ゲームSNS統合コンポーネント
│   │   └── sections/
│   │       ├── HeroSection.astro     # メインビジュアル（Profile API連携）
│   │       ├── AboutSection.astro    # 自己紹介・経歴タイムライン（Profile API連携・タグフィルター）
│   │       ├── SkillsSection.astro   # 技術スキル（Skills API・固定カテゴリ順・レベルソート・アンカーID）
│   │       ├── OpusSection.astro     # 作品・プロジェクト（Opus API・カテゴリフィルター・スキルタグ）
│   │       ├── JourneySection.astro  # 日本8地方・都道府県別旅記録（旅・聖地巡礼・テーマへの入口）
│   │       └── GamesSection.astro    # ゲーム関連（Games API連携）
│   │   └── journey/
│   │       └── PostGrid.astro    # 投稿サムネ一覧（県・旅・聖地巡礼・テーマで共用）
│   ├── lib/
│   │   ├── microcms.ts           # microCMS API共通ユーティリティ（型定義・fetch関数・SKILL_CATEGORY_SLUG）
│   │   └── journey.ts            # Journey のビルド時データ読み出し（外部サービスを呼ばない）
│   ├── layouts/
│   │   └── Layout.astro          # 基本レイアウト
│   ├── pages/
│   │   ├── index.astro           # メインページ
│   │   ├── opus/
│   │   │   └── [slug].astro      # Opus詳細ページ（getStaticPaths自動生成）
│   │   └── journey/
│   │       ├── [slug].astro      # 都道府県ページ（訪問済みの県すべて）
│   │       ├── trips/            # 旅の一覧と個別ページ（年別／地方別の切り替え）
│   │       ├── pilgrimage/       # 聖地巡礼の一覧と作品ページ
│   │       └── themes/           # テーマの一覧と個別ページ
│   └── styles/
│       └── global.css            # グローバルスタイル
├── public/
│   ├── images/                   # 静的画像
│   └── journey/thumbs/           # 投稿サムネ 1,017枚（480px webp・自前保存）
├── data/
│   ├── ontology/                 # 地名オントロジーと県境ポリゴン（機械生成・候補源）
│   └── journey/                  # 投稿・判定結果・辞書・旅・聖地巡礼・テーマ
├── scripts/
│   ├── ontology/                 # オントロジーと県境データの生成
│   ├── ingest/                   # エクスポート取り込み・API増分取り込み・サムネ生成・permalink取得
│   └── journey/                  # 都道府県の解決・旅/聖地巡礼/テーマの抽出
├── .github/workflows/            # GitHub Actions設定（main への push で本番デプロイ）
├── docker-compose.yml            # Docker Compose設定
├── Dockerfile                    # マルチステージビルド設定
└── nginx.conf                    # Nginx設定
```

### 🐳 Docker & デプロイメント

- **本番URL**: `https://portorifo.riumu.net`
- **Dockerイメージ**: `ghcr.io/torifo/portfolio-astro:latest`
- **ビルド方式**: マルチステージ（ビルダー → Nginx Alpine）
- **Webサーバー**: Nginx on Alpine Linux
- **環境変数**: microCMS API設定を `.env` で管理（git追跡外。CI では GitHub Secrets）
- **存在しない URL**: nginx が 404 を返し、`404.astro` を表示する

#### デプロイフロー

**`main` への push がそのまま本番デプロイです。** 承認の関門はありません。

```
main に push / workflow_dispatch
  └─ .github/workflows/deploy.yml
       ├─ タグ生成（JST の YYYYMMDD-HHMM）
       ├─ microCMS を data/microcms/*.json に取得（失敗した分は前回分が残る）
       ├─ docker build → :{タグ} と :latest を GHCR へ push
       ├─ VPS へ SSH → /home/ubuntu/Web/portfolio-astro/deploy.sh {タグ}
       │                  └─ docker compose pull → down → up -d
       └─ 取得した microCMS を main にコミット（data/microcms は paths-ignore なので再発火しない）
```

ロールバックは VPS で1コマンドです。タグは
[GHCR のパッケージ画面](https://github.com/torifo/portfolio-astro/pkgs/container/portfolio-astro)
か Actions のジョブサマリーで確認できます。

```bash
cd /home/ubuntu/Web/portfolio-astro && ./deploy.sh <戻したいタグ>
```

必要な GitHub Secrets: `GHCR_TOKEN` / `VPS_HOST` / `VPS_USER` / `VPS_SSH_KEY` /
`PUBLIC_MICROCMS_API_KEY` / `PUBLIC_MICROCMS_SERVICE_DOMAIN` / `INSTAGRAM_ACCESS_TOKEN`
（Journey の同期用。詳細は [DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md)）

### 🌟 コンテンツセクション

| セクション | 概要 | データソース |
|-----------|------|------------|
| **Hero** | メインビジュアル・タイトル | microCMS Profile API |
| **About** | 自己紹介・経歴タイムライン・Connect | microCMS Profile API（タグフィルター対応）|
| **Skills** | 技術スキル（8カテゴリ固定順・レベルソート） | microCMS Skills API |
| **Opus** | 作品・プロジェクト・詳細ページ・スキルタグ | microCMS Opus API（カテゴリフィルター対応）|
| **Journey** | 日本8地方・都道府県別旅記録／旅・聖地巡礼・テーマ | ローカルJSON（Instagram エクスポート＋API増分・ビルド時に外部呼び出しなし）|
| **Games** | ゲーム関連情報・SNSリンク | microCMS Games API |

### 🔌 microCMS API連携

- **エンドポイント**: `https://portorifo.microcms.io/api/v1/`
- **Profile** (`/profile`): 名前・肩書き・自己紹介・アバター・メールアドレス・経歴タイムライン
- **Opus** (`/opus?orders=createdAt`): 作品一覧・カテゴリ・関連リンク・サムネイル・使用スキル（`relatedSkill`）
- **Skills** (`/skills`): 技術スキル一覧・カテゴリ・レベル・アイコン・使用作品（`usedIn`）
- **Games** (`/games`): ゲーム情報・関連SNS・タグ
- 全API呼び出しはビルド時のみ実行（SSG）→ APIキーは最終HTMLに含まれない

### 📸 Journey データの更新

**新着は GitHub Actions が取り込んで PR にする。** マージすると本番に出る。
ビルド自体は外部を一切呼ばない。

```
毎日 2:47 JST（GitHub の遅れで実際は5〜7時ごろ。または Actions の「Journey sync」→ Run workflow）
  └─ 新着を取り込み、県・旅を判定 → journey/sync-日付 の PR を作る
       本文: 要確認 / 新着の一覧（旅・撮影日ごと。サムネ・リンク・判定された県）/ 旅の変化
       ├─ 日付の後ろに場所（または「趣味」）を書いた投稿だけで、要確認0件 → そのままマージ
       ├─ それ以外 → PR を開いたまま（確認してマージ）
       └─ 混ざる → 書いた側をマージし、残りを journey/sync-日付-hold の PR にする
```

Instagram API は位置情報を返さないので、投稿するときに本文の日付の行に場所を書く
（2026-09-30 以降の投稿）。サイトに載せたくない投稿は「趣味」と書く。

```
2025-06-28 横浜        … 神奈川県（「横浜➝東京」なら先頭の横浜）。訪問済みの県なら最初の投稿でも自動マージ
2025-10-04 趣味        … サイトに載せない（記録には残す）
```

PR の「要確認」は、本番で実際に起きた誤りの型を機械で探したもの
（旅タグの語で県が決まった、初めての県、同じ日の投稿と県が違う、旅の期間外、撮影日が不明、など）。
直すときは PR のブランチで次のファイルを直し、`npm run journey:build` してコミットする。

| 直したいもの | ファイル | 書き方 |
|---|---|---|
| 県 | `data/journey/overrides.json` | `"投稿ID": ["13"]` または `"タグ": ["14"]`（タグならそのタグの投稿すべてに効く） |
| 撮影日 | `data/journey/date_overrides.json` | `"投稿ID": "2023-09-05"` |
| 再利用できる地名 | `data/journey/gazetteer.json` | `"地名": ["27"]` |

Instagram 側のキャプションを直しても、取り込み済みの投稿には届かない（新着しか読まないため）。

手元で回す場合:

```bash
# 新着だけを API から取り込む（トークンは環境変数か ~/dev/.env.dev）
npm run journey:sync

# 同期 PR を手元から作る（別の作業ツリーで行うので手元は触らない）
bash scripts/journey/auto_sync.sh            # --dry-run で PR を作らない

# エクスポート zip から作り直す（EXIF の GPS が取れるのはこちらだけ）
python3 scripts/ingest/parse_export.py <エクスポートの展開先>
python3 scripts/ingest/build_thumbs.py
python3 scripts/ingest/fetch_permalinks.py
npm run journey:build

# 文字だけの県判定の精度を測る（判定の規則を変える前に --save、変えた後に --compare）
python3 scripts/journey/eval_resolve.py
```

撮影地の座標（`data/journey/gps.json`）は公開しないので Git に入れていない。Actions など
座標が無い環境では、GPS で決まった判定を前回の結果から引き継ぐ（座標がある環境と結果は同じ）。
仕組みの詳細は [設計書の 2026-09-29・2026-10-04 改訂](docs/superpowers/specs/2026-09-11-journey-instagram-design.md)、
[精度改善の設計](docs/superpowers/specs/2026-09-30-journey-accuracy-design.md)、
[PR の分割の設計](docs/superpowers/specs/2026-10-04-journey-sync-pr-split-design.md) にある。

### ✅ 実装済み機能

- [x] microCMS Profile API連携（Hero・About・Connect）
- [x] microCMS Opus API連携（作品一覧・カテゴリフィルター）
- [x] microCMS Skills API連携（技術スキル一覧・8カテゴリ固定順・レベル降順ソート）
- [x] microCMS Games API連携（ゲーム情報・SNS）
- [x] Opus詳細ページ自動生成（`/opus/[slug]`）
- [x] About経歴タイムライン タグフィルター（Academic / Technology / Opus / Pulse / Community）
- [x] OpusのrelatedSkillタグ表示（カテゴリ別グループ・Skillsセクションへのアンカーリンク）
- [x] 日の出・日没APIによる自動テーマ切り替え（JSTの日付変わりでキャッシュ自動リセット）
- [x] Journey 8地方・都道府県別訪問管理（訪問済み地方を動的カウント・地方の形のシルエット・9枠目に海外）
- [x] Journey × Instagram 連携（投稿1,063件・都道府県100%解決・LLM呼び出しなし）
- [x] 都道府県ページ自動生成（`/journey/[slug]`・訪問済み40県）
- [x] 旅・聖地巡礼・テーマの各ページ（旅32件・聖地巡礼5作品・テーマ13。同じ投稿が複数ページに出る）
- [x] 投稿サムネの自前保存（480px webp・Instagram の media URL 失効対策）
- [x] 新着の自動取り込み（毎日 GitHub Actions が PR を作る・手動実行も可）
- [x] 日付の後ろに場所を書いた投稿の自動マージ（混ざれば PR を分ける・「趣味」は載せない）
- [x] 文字だけの県判定の精度測定（`eval_resolve.py`・誤り 8.4%）
- [x] 存在しない URL は 404 を返す（`404.astro`）・プライバシーポリシー・利用規約
- [x] Footerビルド時刻自動表示
- [x] GHCR Docker イメージ管理

---

## English

### 📖 Overview

A modern portfolio website built with Astro and TypeScript. Features microCMS API-driven dynamic content, automatic light/dark theme switching via Sunrise-Sunset API, and high-performance static generation with Astro SSG. Build and deployment environments are separated for efficient resource usage.

### 🛠️ Tech Stack

- **Framework**: Astro (SSG) - Static site generation for fast delivery
- **Styling**: Tailwind CSS - Utility-first CSS
- **Language**: TypeScript - Type safety and code quality
- **CMS**: microCMS - Headless CMS (Profile, Opus, Skills & Games APIs)
- **External API**: Sunrise Sunset API - Auto theme switching
- **Containerization**: Docker (multi-stage: node:alpine → nginx:alpine)
- **Web Server**: Nginx - High-performance static file serving
- **Registry**: GitHub Container Registry (GHCR)

### ✨ Features

- **Responsive Design**: Optimized for mobile to desktop
- **High Performance**: Static site generation with Astro SSG
- **Dynamic Content**: Build-time data fetching from microCMS (Profile, Opus, Skills, Games)
- **Dynamic Routes**: Auto-generated Opus detail pages via `getStaticPaths()`
- **Filter UI**: Category/tag filters in Opus and About sections
- **Skill Tags in Opus**: Each Opus service displays linked skill tags grouped by category; clicking navigates to the corresponding Skills section with smooth scroll
- **Skill Sorting**: Skills auto-sorted by level (desc) then creation date (asc) within each fixed-order category
- **Auto Theme**: Light/dark mode based on Tokyo sunrise/sunset times (cache resets at JST midnight)
- **Real-time Clock**: JST time in header
- **Build Timestamp**: Build date auto-embedded in footer
- **Journey (Instagram)**: Browse travel photos by prefecture, trip, anime pilgrimage and theme. GitHub Actions ingests new posts every morning and opens a pull request for review

### 🐳 Docker & Deployment

- **Production URL**: `https://portorifo.riumu.net`
- **Docker Image**: `ghcr.io/torifo/portfolio-astro:latest`
- **Build**: Multi-stage Docker build (builder → Nginx Alpine)

#### Deployment Flow

**Pushing to `main` deploys to production.** There is no approval gate.

```
push to main / workflow_dispatch
  └─ .github/workflows/deploy.yml
       ├─ tag from JST date (YYYYMMDD-HHMM)
       ├─ fetch microCMS into data/microcms/*.json (keeps the last good copy on failure)
       ├─ docker build → push :{tag} and :latest to GHCR
       └─ ssh to VPS → /home/ubuntu/Web/portfolio-astro/deploy.sh {tag}
                          └─ docker compose pull → down → up -d
```

Rollback is one command on the VPS. Tags are listed on the
[GHCR package page](https://github.com/torifo/portfolio-astro/pkgs/container/portfolio-astro)
and in each Actions job summary.

```bash
cd /home/ubuntu/Web/portfolio-astro && ./deploy.sh <tag>
```

Required GitHub secrets: `GHCR_TOKEN`, `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`,
`PUBLIC_MICROCMS_API_KEY`, `PUBLIC_MICROCMS_SERVICE_DOMAIN`, `INSTAGRAM_ACCESS_TOKEN`

#### Journey Sync

`.github/workflows/journey-sync.yml` runs every night at 2:47 JST (or on demand via
*Run workflow*). It ingests new Instagram posts, resolves prefectures and trips, and opens a
`journey/sync-*` pull request with automated checks. Merging it deploys as usual. Posts whose
caption names a place right after the date (or `趣味` to keep a post off the site) are merged
automatically with `GHCR_TOKEN`; the rest stay open for review in a separate PR. See
[docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) for details.

### 🔌 microCMS API

- **Base**: `https://portorifo.microcms.io/api/v1/`
- **Profile** (`/profile`): Name, title, introduction, avatar, emails, history timeline
- **Opus** (`/opus?orders=createdAt`): Works, categories, related links, thumbnails, skill tags (`relatedSkill`)
- **Skills** (`/skills`): Tech skills, categories, levels, icons, linked works (`usedIn`)
- **Games** (`/games`): Game info, related SNS, tags
- All API calls run at **build time only** (SSG) — API keys are never exposed to browsers
