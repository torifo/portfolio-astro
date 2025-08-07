# Toriforium Portfolio

## 日本語

### 📖 概要

AstroとReactを使用して構築されたモダンなポートフォリオWebサイトです。クリーンなデザインと滑らかなユーザーエクスペリエンスを特徴としており、個人のスキル、経歴、作品、趣味などを紹介するためのサイトです。Build環境とデプロイ環境を分離して，リソースに配慮した設計で開発を行っています．

### 🛠️ 使用技術

- **フレームワーク**: Astro 5.12.0 - 静的サイト生成による高速なWebサイト
- **UIライブラリ**: React 19.1.0 - インタラクティブなコンポーネント
- **スタイリング**: Tailwind CSS 4.1.11 - ユーティリティファーストのCSS
- **言語**: TypeScript - 型安全性とコード品質の向上
- **バックエンド**: microCMS - ヘッドレスCMSによるコンテンツ管理
- **外部API**: Sunrise Sunset API - 日の出・日没時刻による自動テーマ切り替え
- **コンテナ化**: Docker - アプリケーションのコンテナ化とデプロイメント
- **Webサーバー**: Nginx - 高速な静的ファイル配信
- **CI/CD**: GitHub Actions - dockerコンテナのpackageによる共有

### ✨ 特徴

- **レスポンシブデザイン**: モバイルからデスクトップまで対応
- **高速パフォーマンス**: Astroの静的サイト生成により最適化
- **モダンなUI**: グラデーションエフェクトとアニメーション
- **コンポーネント指向**: 再利用可能な設計
- **動的コンテンツ**: microCMS APIによる柔軟なコンテンツ管理
- **自動テーマ切り替え**: 日の出・日没時刻に基づくライト/ダークモード自動切り替え
- **リアルタイム時計**: JST時刻のリアルタイム表示
- **プレ公開**: Dockerコンテナによる開発環境でのテスト運用
- **手動デプロイ**: Docker Composeを使った柔軟なデプロイメント

### 📁 プロジェクト構造

```
/
├── src/
│   ├── components/          # 再利用可能なコンポーネント
│   │   ├── Header.astro     # ヘッダーナビゲーション
│   │   ├── ThemeToggle.astro # テーマ切り替えと時間表示
│   │   ├── Footer.astro     # フッター
│   │   ├── GameSNS.astro    # ゲームSNS統合コンポーネント
│   │   └── sections/        # セクション別コンポーネント
│   │       ├── HeroSection.astro     # メインビジュアル
│   │       ├── AboutSection.astro    # 自己紹介
│   │       ├── SkillsSection.astro   # 技術スキル
│   │       ├── JourneySection.astro  # 経歴・履歴
│   │       ├── OpusSection.astro     # 作品・プロジェクト
│   │       └── GamesSection.astro    # ゲーム関連
│   ├── layouts/
│   │   └── Layout.astro     # 基本レイアウト
│   ├── pages/
│   │   └── index.astro      # メインページ
│   ├── styles/
│   │   └── global.css       # グローバルスタイル
│   └── content.config.mjs   # コンテンツ設定
├── .github/workflows/       # GitHub Actions設定
│   └── deploy.yml          # デプロイメントワークフロー
├── image/icon/              # アイコン・画像素材
├── public/                  # 静的ファイル
├── docker-compose.yml       # Docker Compose設定
├── Dockerfile              # Docker設定
├── nginx.conf              # Nginx設定
├── DEPLOYMENT.md           # デプロイメント手順書
├── TROUBLESHOOTING.md      # トラブルシューティングガイド
└── 設定ファイル (astro.config.mjs, tailwind.config.mjs等)
```

### 🐳 Docker & デプロイメント構成

- **本番URL**: `https://portorifo.riumu.net`
- **Dockerイメージ**: `ghcr.io/torifo/portfolio-astro:latest`
- **Webサーバー**: Nginx on Alpine Linux
- **ネットワーク**: `global-proxy-network` (リバースプロキシ対応)
- **SSL証明書**: Let's Encrypt自動取得
- **環境変数**: microCMS API設定を環境変数で管理

### 🌟 コンテンツセクション

- **Hero**: メインビジュアルと自己紹介
- **About**: 詳細なプロフィールと背景
- **Skills**: 技術スキルと専門知識（microCMS APIから動的取得）
- **Journey**: キャリアの歩みと経験
- **Opus**: 制作物とプロジェクト紹介
- **Games**: ゲームに関する趣味や活動

### 🚧 開発状況・今後の予定

- **現在の状況**: 開発段階・プレ公開でテスト運用中、継続的な機能改善とUI最適化を実施
- **API連携**: Skillsセクションでは既にmicroCMS APIを使用してデータを動的取得
- **新機能完了**: 日の出・日没APIによる自動テーマ切り替え機能を実装済み
- **インフラ整備**: Docker化による効率的なデプロイメント環境を構築
- **今後の展開**: 他のセクションにもAPI連携を拡張し、より柔軟なコンテンツ管理を実現予定
- **計画中の機能**: プロジェクト情報の動的管理、経歴データのAPI化、ゲーム情報の自動更新、自動デプロイパイプライン

### 🌅 最新機能 - テーマシステム & Docker化 (2025年1月)

**テーマ機能:**
- **自動テーマ切り替え**: 東京の日の出・日没時刻に基づいて自動的にライト/ダークモードを切り替え
- **リアルタイム時計**: ヘッダーにJST時刻をリアルタイム表示
- **手動テーマ選択**: ドロップダウンメニューでライト/ダーク/自動モードを選択可能
- **動的アイコン**: テーマに応じて太陽/月のアイコンが切り替わる
- **UI最適化**: ライトモードでの文字の視認性を大幅改善、タブレット・モバイル端末でのUX向上

**インフラ改善:**
- **Docker化**: マルチステージビルドによる効率的なコンテナ化
- **Container Registry**: GitHub Container Registryでのイメージ管理
- **開発・本番環境分離**: 効率的なリソース使用とデプロイメント
- **SSL/TLS**: Let's Encryptによる自動SSL証明書取得・更新

### 🔄 デプロイメントワークフロー

1. **開発環境**: `/home/ubuntu/Web/portfolio-astro` (VPS) - コード修正・テスト
2. **ビルド環境**: WSLでのDockerイメージビルド・Container Registryへプッシュ
3. **プレ公開環境**: `https://portorifo.riumu.net` でのコンテナテスト運用

詳細は [`DEPLOYMENT.md`](DEPLOYMENT.md) を参照してください。

---

## English

### 📖 Overview

A modern portfolio website built with Astro and React, featuring clean design and smooth user experience. This site showcases personal skills, career history, projects, and interests in an elegant and professional manner.

### 🛠️ Tech Stack

- **Framework**: Astro 5.12.0 - Fast websites with static site generation
- **UI Library**: React 19.1.0 - Interactive components
- **Styling**: Tailwind CSS 4.1.11 - Utility-first CSS framework
- **Language**: TypeScript - Type safety and code quality
- **Backend**: microCMS - Headless CMS for content management
- **External API**: Sunrise Sunset API - Automatic theme switching based on sunrise/sunset times
- **Containerization**: Docker - Application containerization and deployment
- **Web Server**: Nginx - High-performance static file serving
- **CI/CD**: GitHub Actions - Automated build and deployment

### ✨ Features

- **Responsive Design**: Optimized for mobile to desktop
- **High Performance**: Optimized with Astro's static site generation
- **Modern UI**: Gradient effects and smooth animations
- **Component-Oriented**: Reusable and maintainable architecture
- **Dynamic Content**: Flexible content management with microCMS API
- **Auto Theme Switching**: Automatic light/dark mode based on sunrise/sunset times
- **Real-time Clock**: JST time display in real-time
- **Production Ready**: Stable operation with Docker containers in production environment
- **Automated Deployment**: Workflow automation with GitHub Actions

### 📁 Project Structure

```
/
├── src/
│   ├── components/          # Reusable components
│   │   ├── Header.astro     # Header navigation
│   │   ├── ThemeToggle.astro # Theme switching and time display
│   │   ├── Footer.astro     # Footer
│   │   ├── GameSNS.astro    # Game SNS integration component
│   │   └── sections/        # Section components
│   │       ├── HeroSection.astro     # Main visual
│   │       ├── AboutSection.astro    # About me
│   │       ├── SkillsSection.astro   # Technical skills
│   │       ├── JourneySection.astro  # Career timeline
│   │       ├── OpusSection.astro     # Projects showcase
│   │       └── GamesSection.astro    # Gaming interests
│   ├── layouts/
│   │   └── Layout.astro     # Base layout
│   ├── pages/
│   │   └── index.astro      # Main page
│   ├── styles/
│   │   └── global.css       # Global styles
│   └── content.config.mjs   # Content configuration
├── .github/workflows/       # GitHub Actions configuration
│   └── deploy.yml          # Deployment workflow
├── image/icon/              # Icons and images
├── public/                  # Static files
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile              # Docker configuration
├── nginx.conf              # Nginx configuration
├── DEPLOYMENT.md           # Deployment documentation
├── TROUBLESHOOTING.md      # Troubleshooting guide
└── Configuration files (astro.config.mjs, tailwind.config.mjs, etc.)
```

### 🐳 Docker & Deployment Configuration

- **Production URL**: `https://portorifo.riumu.net`
- **Docker Image**: `ghcr.io/torifo/portfolio-astro:latest`
- **Web Server**: Nginx on Alpine Linux
- **Network**: `global-proxy-network` (reverse proxy ready)
- **SSL Certificate**: Automatic Let's Encrypt acquisition
- **Environment Variables**: microCMS API settings managed via environment variables

### 🌟 Content Sections

- **Hero**: Main visual and introduction
- **About**: Detailed profile and background
- **Skills**: Technical skills and expertise (dynamically fetched from microCMS API)
- **Journey**: Career timeline and experience
- **Opus**: Projects and works showcase
- **Games**: Gaming interests and activities

### 🚧 Development Status & Future Plans

- **Current Status**: Production ready with continuous feature improvements and UI optimization
- **API Integration**: Skills section already uses microCMS API for dynamic data retrieval
- **New Feature Completed**: Automatic theme switching based on sunrise/sunset API implementation
- **Infrastructure Completed**: Docker containerization and GitHub Actions automated deployment pipeline established
- **Future Expansion**: Planning to extend API integration to other sections for more flexible content management
- **Planned Features**: Dynamic project information management, API-driven career data, automated game information updates

### 🌅 Latest Features - Theme System & Deployment Automation (January 2025)

**Theme Features:**
- **Auto Theme Switching**: Automatically switches between light/dark mode based on Tokyo's sunrise/sunset times
- **Real-time Clock**: JST time display in header with real-time updates
- **Manual Theme Selection**: Dropdown menu for light/dark/auto mode selection
- **Dynamic Icons**: Sun/moon icons change according to current theme
- **UI Optimization**: Significantly improved text visibility in light mode, enhanced tablet/mobile UX

**Deployment Automation:**
- **Docker Integration**: Efficient containerization with multi-stage builds
- **GitHub Actions**: Automated build, test, and deployment workflows
- **Container Registry**: Image management with GitHub Container Registry
- **Production Environment**: Container orchestration on VPS
- **SSL/TLS**: Automatic SSL certificate acquisition and renewal with Let's Encrypt

### 🔄 Deployment Workflow

1. **Development Environment**: `/home/ubuntu/Web/portfolio-astro` (VPS)
2. **Build Environment**: Docker image building on WSL
3. **GitHub Actions**: Automated CI/CD pipeline
4. **Production Environment**: Container operation at `https://portorifo.riumu.net`

For detailed instructions, see [`DEPLOYMENT.md`](DEPLOYMENT.md).