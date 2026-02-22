# Toriforium Portfolio

## 日本語

### 📖 概要

AstroとTypeScriptを使用して構築されたモダンなポートフォリオWebサイトです。microCMS APIによる動的コンテンツ管理、日の出・日没APIによる自動テーマ切り替え、Astro SSG による高速な静的サイト生成を特徴としています。ビルド環境とデプロイ環境を分離し、リソースに配慮した設計で開発しています。

### 🛠️ 使用技術

- **フレームワーク**: Astro (SSG) - 静的サイト生成による高速配信
- **スタイリング**: Tailwind CSS - ユーティリティファーストのCSS
- **言語**: TypeScript - 型安全性とコード品質の向上
- **CMS**: microCMS - ヘッドレスCMSによるコンテンツ管理（Profile・Opus API）
- **外部API**: Sunrise Sunset API - 日の出・日没時刻による自動テーマ切り替え
- **コンテナ化**: Docker (multi-stage build: node:alpine → nginx:alpine)
- **Webサーバー**: Nginx - 高速な静的ファイル配信
- **レジストリ**: GitHub Container Registry (GHCR)

### ✨ 特徴

- **レスポンシブデザイン**: モバイルからデスクトップまで対応
- **高速パフォーマンス**: Astro SSG による最適化された静的サイト
- **モダンUI**: グラデーションエフェクトとアニメーション
- **動的コンテンツ**: microCMS APIによるビルド時データ取得（Profile・Opus）
- **動的ルーティング**: `getStaticPaths()` による Opus 詳細ページ自動生成
- **カテゴリ/タグフィルター**: OpusSection・AboutSection でのクライアント側絞り込み
- **自動テーマ切り替え**: 日の出・日没時刻に基づくライト/ダークモード
- **リアルタイム時計**: ヘッダーにJST時刻をリアルタイム表示
- **ビルド時刻表示**: フッターにビルド日時を自動埋め込み（JST）
- **Instagram連携**: Journey セクションで旅の写真アカウントとリンク

### 📁 プロジェクト構造

```
/
├── src/
│   ├── components/
│   │   ├── Header.astro          # ヘッダーナビゲーション
│   │   ├── ThemeToggle.astro     # テーマ切り替え・時刻表示
│   │   ├── Footer.astro          # フッター（ビルド時刻自動表示）
│   │   ├── DetailHeader.astro    # Opus詳細ページ用ヘッダー
│   │   ├── GameSNS.astro         # ゲームSNS統合コンポーネント
│   │   └── sections/
│   │       ├── HeroSection.astro     # メインビジュアル（Profile API連携）
│   │       ├── AboutSection.astro    # 自己紹介・経歴タイムライン（Profile API連携・タグフィルター）
│   │       ├── SkillsSection.astro   # 技術スキル
│   │       ├── OpusSection.astro     # 作品・プロジェクト（Opus API連携・カテゴリフィルター）
│   │       ├── JourneySection.astro  # 日本8地方・都道府県別旅記録
│   │       └── GamesSection.astro    # ゲーム関連
│   ├── lib/
│   │   └── microcms.ts           # microCMS API共通ユーティリティ（型定義・fetch関数）
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
| **Skills** | 技術スキル | 静的データ |
| **Opus** | 作品・プロジェクト・詳細ページ | microCMS Opus API（カテゴリフィルター対応）|
| **Journey** | 日本8地方・都道府県別旅記録 | 静的データ（訪問済み管理）|
| **Games** | ゲーム関連情報 | 外部API |

### 🔌 microCMS API連携

- **エンドポイント**: `https://portorifo.microcms.io/api/v1/`
- **Profile** (`/profile`): 名前・肩書き・自己紹介・アバター・メールアドレス・経歴タイムライン
- **Opus** (`/opus?orders=createdAt`): 作品一覧・カテゴリ・関連リンク・サムネイル
- 全API呼び出しはビルド時のみ実行（SSG）→ APIキーは最終HTMLに含まれない

### ✅ 実装済み機能

- [x] microCMS Profile API連携（Hero・About・Connect）
- [x] microCMS Opus API連携（作品一覧・カテゴリフィルター）
- [x] Opus詳細ページ自動生成（`/opus/[slug]`）
- [x] About経歴タイムライン タグフィルター（Academic / Technology / Opus / Pulse / Community）
- [x] 日の出・日没APIによる自動テーマ切り替え
- [x] Journey 8地方・都道府県別訪問管理（静的仮データ・API連携は未実装）
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
- **CMS**: microCMS - Headless CMS (Profile & Opus APIs)
- **External API**: Sunrise Sunset API - Auto theme switching
- **Containerization**: Docker (multi-stage: node:alpine → nginx:alpine)
- **Web Server**: Nginx - High-performance static file serving
- **Registry**: GitHub Container Registry (GHCR)

### ✨ Features

- **Responsive Design**: Optimized for mobile to desktop
- **High Performance**: Static site generation with Astro SSG
- **Dynamic Content**: Build-time data fetching from microCMS (Profile & Opus)
- **Dynamic Routes**: Auto-generated Opus detail pages via `getStaticPaths()`
- **Filter UI**: Category/tag filters in Opus and About sections
- **Auto Theme**: Light/dark mode based on Tokyo sunrise/sunset times
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
- **Opus** (`/opus?orders=createdAt`): Works, categories, related links, thumbnails
- All API calls run at **build time only** (SSG) — API keys are never exposed to browsers
