# デプロイメントワークフロー

## 概要

このプロジェクトは以下の2つの環境で構成されています：

- **デプロイ環境 (VPS)**: `/home/ubuntu/Web/portfolio-astro` - 修正・追加作業を行う環境
- **ビルド環境 (WSL)**: `ssh toriforiumu@wsl` - ビルドとコンテナプッシュを行う環境

## デプロイ手順

### 1. デプロイ環境での作業 (VPS)

```bash
# 現在の環境: /home/ubuntu/Web/portfolio-astro
# 1. コードの修正・追加を行う
# 2. 変更をコミット
git add .
git commit -m "feat: your changes description"

# 3. GitHubにプッシュ
git push origin deploy/docker-setup
```

### 2. ビルド環境での作業 (WSL)

```bash
# SSH接続
ssh toriforiumu@wsl

# プロジェクトディレクトリに移動
cd portfolio-astro

# 最新のコードをプル
git pull origin deploy/docker-setup

# 依存関係のインストール（必要に応じて）
npm ci

# .envファイルの確認・作成
# PUBLIC_MICROCMS_API_KEY=your_api_key
# PUBLIC_MICROCMS_SERVICE_DOMAIN=your_service_domain

# ビルド実行
npm run build

# Dockerイメージのビルド
docker build -t portfolio-frontend .

# GitHub Container Registryにログイン
# docker login ghcr.io -u torifo -p YOUR_GITHUB_TOKEN(完了済み)

# イメージにタグ付け
docker tag portfolio-frontend ghcr.io/torifo/portfolio-astro:latest

# GitHub Container Registryにプッシュ
docker push ghcr.io/torifo/portfolio-astro:latest
```

### 3. デプロイ環境での最終作業 (VPS)

```bash
# 現在の環境: /home/ubuntu/Web/portfolio-astro
# 新しいDockerイメージをプル
docker pull ghcr.io/torifo/portfolio-astro:latest

# 現在のコンテナを停止・削除（必要に応じて）
docker compose down

# 新しいコンテナを起動
docker compose up -d

# コンテナの状態確認
docker compose ps
docker compose logs portfolio-frontend
```

## 自動化の段階的改善案

### Phase 1: 通知システム
- ビルド完了時にSlack/Discord通知
- デプロイ完了時に通知

### Phase 2: 部分的自動化
- GitHub Actionsでビルド環境への自動デプロイ
- Webhookを使用したVPS環境への通知

### Phase 3: 完全自動化
- プッシュ時の完全自動デプロイパイプライン
- ロールバック機能

## 現在のコンテナ情報

- **イメージ**: `ghcr.io/torifo/portfolio-astro:latest`
- **コンテナ名**: `portfolio-frontend`
- **ドメイン**: `portorifo.riumu.net`
- **ネットワーク**: `global-proxy-network`

## トラブルシューティング

### コンテナが起動しない場合
```bash
# ログを確認
docker compose logs portfolio-frontend

# .envファイルの確認
cat .env

# ネットワークの確認
docker network ls
```

### イメージプルエラーの場合
```bash
# 認証情報の確認
docker login ghcr.io

# 手動でのイメージプル
docker pull ghcr.io/torifo/portfolio-astro:latest
```

## 注意事項

- ビルド環境では必ず最新のコードをプルしてからビルドを実行する
- .envファイルの環境変数が正しく設定されていることを確認する
- プッシュ前にコンテナがローカルで正常に動作することを確認する
- デプロイ後は必ずWebサイトの動作確認を行う