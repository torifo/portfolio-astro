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
- **Instagram連携**: Journey セクションで旅の写真アカウントとリンク

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
│   │       ├── JourneySection.astro  # 日本8地方・都道府県別旅記録
│   │       └── GamesSection.astro    # ゲーム関連（Games API連携）
│   ├── lib/
│   │   └── microcms.ts           # microCMS API共通ユーティリティ（型定義・fetch関数・SKILL_CATEGORY_SLUG）
│   ├── layouts/
│   │   └── Layout.astro          # 基本レイアウト
│   ├── pages/
│   │   ├── index.astro           # メインページ
│   │   └── opus/
│   │       └── [slug].astro      # Opus詳細ページ（getStaticPaths自動生成）
│   └── styles/
│       └── global.css            # グローバルスタイル
├── public/                       # 静的ファイル・画像
├── .github/workflows/            # GitHub Actions設定
├── docker-compose.yml            # Docker Compose設定
├── Dockerfile                    # マルチステージビルド設定
└── nginx.conf                    # Nginx設定
```

### 🐳 Docker & デプロイメント

- **本番URL**: `https://portorifo.riumu.net`
- **Dockerイメージ**: `ghcr.io/torifo/portfolio-astro:latest`
- **ビルド方式**: マルチステージ（ビルダー → Nginx Alpine）
- **Webサーバー**: Nginx on Alpine Linux
- **環境変数**: microCMS API設定を `.env` で管理（git追跡外）

#### デプロイフロー

```
WSL (ローカル)
  └─ build-push.sh (*gitignore)
       ├─ docker build → ghcr.io/torifo/portfolio-astro:{tag}
       └─ docker push → GHCR

VPS (root@162.43.88.107)
  └─ /home/ubuntu/Web/portfolio-astro/
       └─ ./deploy.sh {tag}  →  docker pull & docker compose up -d
```

> `build-push.sh` はローカル開発者専用スクリプトのため `.gitignore` に記載し追跡外としています。

### 🌟 コンテンツセクション

| セクション | 概要 | データソース |
|-----------|------|------------|
| **Hero** | メインビジュアル・タイトル | microCMS Profile API |
| **About** | 自己紹介・経歴タイムライン・Connect | microCMS Profile API（タグフィルター対応）|
| **Skills** | 技術スキル（8カテゴリ固定順・レベルソート） | microCMS Skills API |
| **Opus** | 作品・プロジェクト・詳細ページ・スキルタグ | microCMS Opus API（カテゴリフィルター対応）|
| **Journey** | 日本8地方・都道府県別旅記録 | 静的データ（訪問済み管理）|
| **Games** | ゲーム関連情報・SNSリンク | microCMS Games API |

### 🔌 microCMS API連携

- **エンドポイント**: `https://portorifo.microcms.io/api/v1/`
- **Profile** (`/profile`): 名前・肩書き・自己紹介・アバター・メールアドレス・経歴タイムライン
- **Opus** (`/opus?orders=createdAt`): 作品一覧・カテゴリ・関連リンク・サムネイル・使用スキル（`relatedSkill`）
- **Skills** (`/skills`): 技術スキル一覧・カテゴリ・レベル・アイコン・使用作品（`usedIn`）
- **Games** (`/games`): ゲーム情報・関連SNS・タグ
- 全API呼び出しはビルド時のみ実行（SSG）→ APIキーは最終HTMLに含まれない

### ✅ 実装済み機能

- [x] microCMS Profile API連携（Hero・About・Connect）
- [x] microCMS Opus API連携（作品一覧・カテゴリフィルター）
- [x] microCMS Skills API連携（技術スキル一覧・8カテゴリ固定順・レベル降順ソート）
- [x] microCMS Games API連携（ゲーム情報・SNS）
- [x] Opus詳細ページ自動生成（`/opus/[slug]`）
- [x] About経歴タイムライン タグフィルター（Academic / Technology / Opus / Pulse / Community）
- [x] OpusのrelatedSkillタグ表示（カテゴリ別グループ・Skillsセクションへのアンカーリンク）
- [x] 日の出・日没APIによる自動テーマ切り替え（JSTの日付変わりでキャッシュ自動リセット）
- [x] Journey 8地方・都道府県別訪問管理（静的データ・訪問済み地方を動的カウント）
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

### 🐳 Docker & Deployment

- **Production URL**: `https://portorifo.riumu.net`
- **Docker Image**: `ghcr.io/torifo/portfolio-astro:latest`
- **Build**: Multi-stage Docker build (builder → Nginx Alpine)

#### Deployment Flow

```
Local WSL
  └─ build-push.sh (*gitignored)
       ├─ docker build → ghcr.io/torifo/portfolio-astro:{tag}
       └─ docker push → GHCR

VPS (root@162.43.88.107)
  └─ /home/ubuntu/Web/portfolio-astro/
       └─ ./deploy.sh {tag}  →  docker pull & docker compose up -d
```

### 🔌 microCMS API

- **Base**: `https://portorifo.microcms.io/api/v1/`
- **Profile** (`/profile`): Name, title, introduction, avatar, emails, history timeline
- **Opus** (`/opus?orders=createdAt`): Works, categories, related links, thumbnails, skill tags (`relatedSkill`)
- **Skills** (`/skills`): Tech skills, categories, levels, icons, linked works (`usedIn`)
- **Games** (`/games`): Game info, related SNS, tags
- All API calls run at **build time only** (SSG) — API keys are never exposed to browsers
