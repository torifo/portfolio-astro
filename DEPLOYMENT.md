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
# npm ci

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

## 安全なデプロイ手順（バージョンタグ管理）

### 概要

`:latest`タグを直接上書きすると、問題発生時のロールバックが困難です。
バージョンタグと環境変数を使用することで、現在の安定版を保護しながら新しいビルドをテストできます。

**docker-compose.yml の設定:**
```yaml
image: ghcr.io/torifo/portfolio-astro:${IMAGE_TAG:-latest}
```
環境変数`IMAGE_TAG`でバージョンを指定。未設定時は`latest`を使用。

---

### WSL環境での作業（ビルドとプッシュ）

**環境**: `ssh toriforiumu@wsl` → `cd portfolio-astro`

**注意点**:
- 必ず最新のコードをプルしてからビルド
- バージョンタグは日付ベース（YYYYMMDD-HHMM形式）
- **:latestタグは更新しない**（テスト完了後のみ）

```bash
# 1. 最新コードをプル
git pull origin deploy/docker-setup

# 2. ビルド実行
npm run build

# 3. バージョンタグを生成してDockerイメージをビルド
VERSION=$(date +%Y%m%d-%H%M)
docker build -t ghcr.io/torifo/portfolio-astro:${VERSION} .

# 4. GHCRにバージョンタグをプッシュ（:latestは更新しない）
docker push ghcr.io/torifo/portfolio-astro:${VERSION}

# 5. バージョン番号を記録（VPSで使用）
echo "Pushed version: ${VERSION}"
```

---

### VPS環境での作業（テストとデプロイ）

**環境**: `/home/ubuntu/Web/portfolio-astro`

**注意点**:
- WSLで表示されたバージョン番号を正確に使用
- docker composeコマンドで環境変数を指定
- テスト完了後のみ:latestタグを更新

#### ステップ1: 新バージョンのテスト

```bash
# 1. バージョン番号を設定（WSLで表示された値）
VERSION="20250113-1430"  # 例

# 2. 新しいイメージをプル
IMAGE_TAG=${VERSION} docker compose pull

# 3. 現在のコンテナを停止
docker compose down

# 4. 新バージョンで起動
IMAGE_TAG=${VERSION} docker compose up -d

# 5. 動作確認
docker compose ps
docker compose logs -f portfolio-frontend
# ブラウザで確認: https://portorifo.riumu.net
```

#### ステップ2: 問題なければ:latestタグを更新（WSL環境で実行）

```bash
# WSL環境に戻る
ssh toriforiumu@wsl
cd portfolio-astro

# テスト済みバージョンに:latestタグを付与
VERSION="20250113-1430"
docker tag ghcr.io/torifo/portfolio-astro:${VERSION} ghcr.io/torifo/portfolio-astro:latest
docker push ghcr.io/torifo/portfolio-astro:latest
```

#### ステップ3: VPS環境で:latestに切り替え

```bash
# VPS環境
docker compose down
docker compose pull  # :latestを取得
docker compose up -d
```

---

### ロールバック手順

**テスト中に問題を発見した場合:**

```bash
# VPS環境
docker compose down

# 環境変数なしで起動（自動的に:latestを使用）
docker compose up -d

# 既存の安定版が起動する
```

**特定バージョンにロールバックする場合:**

```bash
# VPS環境
docker compose down

# 以前の安定版バージョンを指定
IMAGE_TAG=20250110-1200 docker compose pull
IMAGE_TAG=20250110-1200 docker compose up -d
```

**利用可能なバージョンを確認:**

```bash
# GHCRのバージョン一覧を確認
# https://github.com/torifo/portfolio-astro/pkgs/container/portfolio-astro

# ローカルのイメージ確認
docker images ghcr.io/torifo/portfolio-astro
```

---

## 従来のデプロイ手順（参考）

<details>
<summary>従来の:latest直接更新方式（クリックして展開）</summary>

### 1. デプロイ環境での作業 (VPS)

```bash
# 現在の環境: /home/ubuntu/Web/portfolio-astro
git add .
git commit -m "feat: your changes description"
git push origin deploy/docker-setup
```

### 2. ビルド環境での作業 (WSL)

```bash
ssh toriforiumu@wsl
cd portfolio-astro

git pull origin deploy/docker-setup
npm run build

docker build -t portfolio-frontend .
docker tag portfolio-frontend ghcr.io/torifo/portfolio-astro:latest
docker push ghcr.io/torifo/portfolio-astro:latest
```

### 3. デプロイ環境での最終作業 (VPS)

```bash
docker compose pull
docker compose down
docker compose up -d
docker compose ps
docker compose logs portfolio-frontend
```

**注意**: この方法では問題発生時のロールバックが困難です。

</details>

---

## 注意事項

### VPS環境（デプロイ環境）
- テスト時は必ず`IMAGE_TAG`環境変数でバージョンを指定
- 本番適用前に必ず動作確認
- ロールバック時は環境変数なしで起動（:latestを使用）

### WSL環境（ビルド環境）
- 必ず最新のコードをプルしてからビルド実行
- バージョンタグを記録（VPSでの作業に必要）
- :latestタグの更新はテスト完了後のみ

### デプロイ全般
- .envファイルの環境変数が正しく設定されていることを確認
- docker composeコマンドでGHCRからイメージを取得
- 問題発生時は即座にロールバック可能