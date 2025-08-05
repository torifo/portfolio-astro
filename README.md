# Toriforium Portfolio

## 日本語

### 📖 概要

AstroとReactを使用して構築されたモダンなポートフォリオWebサイトです。クリーンなデザインと滑らかなユーザーエクスペリエンスを特徴としており、個人のスキル、経歴、作品、趣味などを紹介するためのサイトです。

### 🛠️ 使用技術

- **フレームワーク**: Astro 5.12.0 - 静的サイト生成による高速なWebサイト
- **UIライブラリ**: React 19.1.0 - インタラクティブなコンポーネント
- **スタイリング**: Tailwind CSS 4.1.11 - ユーティリティファーストのCSS
- **言語**: TypeScript - 型安全性とコード品質の向上
- **バックエンド**: microCMS - ヘッドレスCMSによるコンテンツ管理
- **外部API**: Sunrise Sunset API - 日の出・日没時刻による自動テーマ切り替え

### ✨ 特徴

- **レスポンシブデザイン**: モバイルからデスクトップまで対応
- **高速パフォーマンス**: Astroの静的サイト生成により最適化
- **モダンなUI**: グラデーションエフェクトとアニメーション
- **コンポーネント指向**: 再利用可能な設計
- **動的コンテンツ**: microCMS APIによる柔軟なコンテンツ管理
- **自動テーマ切り替え**: 日の出・日没時刻に基づくライト/ダークモード自動切り替え
- **リアルタイム時計**: JST時刻のリアルタイム表示
- **開発中**: 継続的な機能追加とUI改善を実施中

### 📁 プロジェクト構造

```
/
├── src/
│   ├── components/          # 再利用可能なコンポーネント
│   │   ├── Header.astro     # ヘッダーナビゲーション
│   │   ├── ThemeToggle.astro # テーマ切り替えと時間表示
│   │   ├── Footer.astro     # フッター
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
│   └── styles/
│       └── global.css       # グローバルスタイル
├── image/icon/              # アイコン・画像素材
├── public/                  # 静的ファイル
└── 設定ファイル (astro.config.mjs, tailwind.config.mjs等)
```

### 🌟 コンテンツセクション

- **Hero**: メインビジュアルと自己紹介
- **About**: 詳細なプロフィールと背景
- **Skills**: 技術スキルと専門知識（microCMS APIから動的取得）
- **Journey**: キャリアの歩みと経験
- **Opus**: 制作物とプロジェクト紹介
- **Games**: ゲームに関する趣味や活動

### 🚧 開発状況・今後の予定

- **現在の状況**: 開発段階・継続的な機能追加中
- **API連携**: Skillsセクションでは既にmicroCMS APIを使用してデータを動的取得
- **新機能完了**: 日の出・日没APIによる自動テーマ切り替え機能を実装済み
- **今後の展開**: 他のセクションにもAPI連携を拡張し、より柔軟なコンテンツ管理を実現予定
- **計画中の機能**: プロジェクト情報の動的管理、経歴データのAPI化、ゲーム情報の自動更新

### 🌅 最新機能 - ナイトモード (2025年1月)

- **自動テーマ切り替え**: 東京の日の出・日没時刻に基づいて自動的にライト/ダークモードを切り替え
- **リアルタイム時計**: ヘッダーにJST時刻をリアルタイム表示
- **手動テーマ選択**: ドロップダウンメニューでライト/ダーク/自動モードを選択可能
- **動的アイコン**: テーマに応じて太陽/月のアイコンが切り替わる
- **UI最適化**: ライトモードでの文字の視認性を大幅改善

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

### ✨ Features

- **Responsive Design**: Optimized for mobile to desktop
- **High Performance**: Optimized with Astro's static site generation
- **Modern UI**: Gradient effects and smooth animations
- **Component-Oriented**: Reusable and maintainable architecture
- **Dynamic Content**: Flexible content management with microCMS API
- **Auto Theme Switching**: Automatic light/dark mode based on sunrise/sunset times
- **Real-time Clock**: JST time display in real-time
- **In Development**: Continuous feature additions and UI improvements

### 📁 Project Structure

```
/
├── src/
│   ├── components/          # Reusable components
│   │   ├── Header.astro     # Header navigation
│   │   ├── Footer.astro     # Footer
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
│   └── styles/
│       └── global.css       # Global styles
├── image/icon/              # Icons and images
├── public/                  # Static files
└── Configuration files (astro.config.mjs, tailwind.config.mjs, etc.)
```

### 🌟 Content Sections

- **Hero**: Main visual and introduction
- **About**: Detailed profile and background
- **Skills**: Technical skills and expertise (dynamically fetched from microCMS API)
- **Journey**: Career timeline and experience
- **Opus**: Projects and works showcase
- **Games**: Gaming interests and activities

### 🚧 Development Status & Future Plans

- **Current Status**: In development with continuous feature additions
- **API Integration**: Skills section already uses microCMS API for dynamic data retrieval
- **New Feature Completed**: Automatic theme switching based on sunrise/sunset API implementation
- **Future Expansion**: Planning to extend API integration to other sections for more flexible content management
- **Planned Features**: Dynamic project information management, API-driven career data, automated game information updates

### 🌅 Latest Feature - Night Mode (January 2025)

- **Auto Theme Switching**: Automatically switches between light/dark mode based on Tokyo's sunrise/sunset times
- **Real-time Clock**: JST time display in header with real-time updates
- **Manual Theme Selection**: Dropdown menu for light/dark/auto mode selection
- **Dynamic Icons**: Sun/moon icons change according to current theme
- **UI Optimization**: Significantly improved text visibility in light mode