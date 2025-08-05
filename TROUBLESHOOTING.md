# トラブルシューティング

このドキュメントでは、Astro製ポートフォリオサイトの開発・デプロイ時に発生する可能性がある問題とその解決方法について説明します。

## 目次

- [開発環境の問題](#開発環境の問題)
- [ビルド時の問題](#ビルド時の問題)
- [Docker関連の問題](#docker関連の問題)
- [API関連の問題](#api関連の問題)
- [テーマ機能の問題](#テーマ機能の問題)

## 開発環境の問題

### Node.jsのバージョン不一致

**症状**: `npm install`や`npm run dev`でエラーが発生する

**解決方法**:
```bash
# Node.jsのバージョンを確認
node --version

# 推奨バージョン: 18.x以上
# nvm使用時
nvm install 18
nvm use 18
```

### 依存関係の問題

**症状**: パッケージのインストールエラーまたは実行時エラー

**解決方法**:
```bash
# node_modulesとlock fileを削除
rm -rf node_modules package-lock.json

# 依存関係を再インストール
npm install

# または yarn使用時
rm -rf node_modules yarn.lock
yarn install
```

## ビルド時の問題

### TypeScriptエラー

**症状**: ビルド時にTypeScriptの型エラーが発生

**解決方法**:
```bash
# 型チェックを実行
npm run build

# または個別に確認
npx tsc --noEmit
```

### 環境変数の設定不備

**症状**: microCMS APIからデータが取得できない

**解決方法**:
```bash
# .envファイルの確認
cat .env

# 必要な環境変数
PUBLIC_MICROCMS_API_KEY=your_api_key
PUBLIC_MICROCMS_SERVICE_DOMAIN=your_service_domain
```

## Docker関連の問題

### コンテナが起動しない

**症状**: `docker compose up`でコンテナが起動に失敗する

**解決方法**:
```bash
# ログを確認
docker compose logs portfolio-frontend

# .envファイルの確認
cat .env

# ネットワークの確認
docker network ls
docker network inspect global-proxy-network
```

### イメージプルエラー

**症状**: GitHub Container Registryからのイメージプルが失敗する

**解決方法**:
```bash
# 認証情報の確認
docker login ghcr.io -u torifo

# 手動でのイメージプル
docker pull ghcr.io/torifo/portfolio-astro:latest

# 認証トークンの再生成が必要な場合
# GitHub > Settings > Developer settings > Personal access tokens
```

### ポート競合

**症状**: 指定されたポートが既に使用中

**解決方法**:
```bash
# ポートの使用状況を確認
netstat -tulpn | grep :80
lsof -i :80

# 競合するプロセスを停止
sudo kill <PID>

# または docker-compose.ymlでポートを変更
```

## API関連の問題

### microCMS APIエラー

**症状**: スキルデータやゲームデータが表示されない

**解決方法**:
```bash
# APIキーの確認
echo $PUBLIC_MICROCMS_API_KEY

# ドメインの確認
echo $PUBLIC_MICROCMS_SERVICE_DOMAIN

# ブラウザの開発者ツールでネットワークタブを確認
# 401エラー: APIキーが無効
# 404エラー: ドメインが間違っている
```

### Sunrise Sunset APIエラー

**症状**: テーマの自動切り替えが動作しない

**解決方法**:
```javascript
// ブラウザのコンソールでエラーを確認
// F12 > Console

// 手動でAPIをテスト
fetch('https://api.sunrise-sunset.org/json?lat=35.6762&lng=139.6503&formatted=0')
  .then(response => response.json())
  .then(data => console.log(data));
```

## テーマ機能の問題

### テーマが切り替わらない

**症状**: ライト/ダークモードの切り替えが動作しない

**解決方法**:
```javascript
// ブラウザコンソールで確認
console.log(document.body.classList);

// 手動でテーマを切り替えてテスト
document.body.classList.add('light-mode');
document.body.classList.remove('night-mode');
```

### 時間表示の問題

**症状**: 現在時刻や日の出・日没時刻が正しく表示されない

**解決方法**:
```javascript
// タイムゾーンの確認
console.log(Intl.DateTimeFormat().resolvedOptions().timeZone);

// 日本時間での時刻確認
console.log(new Date().toLocaleString('ja-JP', {timeZone: 'Asia/Tokyo'}));
```

### CSSスタイルが適用されない

**症状**: ライトモードでの文字が見えない

**解決方法**:
```css
/* ブラウザの開発者ツールでスタイルを確認 */
/* F12 > Elements > Styles */

/* CSSファイルの再読み込み */
/* Ctrl+F5 または Cmd+Shift+R */
```

## 一般的な解決手順

### 1. ログの確認
```bash
# 開発サーバーのログ
npm run dev

# Dockerコンテナのログ
docker compose logs -f portfolio-frontend

# ブラウザの開発者ツール
# F12 > Console, Network, Elements
```

### 2. 環境のリセット
```bash
# 開発環境のリセット
rm -rf node_modules package-lock.json
npm install

# Dockerのリセット
docker compose down
docker compose up -d
```

### 3. キャッシュクリア
```bash
# ブラウザキャッシュのクリア
# Ctrl+Shift+Delete または Cmd+Shift+Delete

# Dockerイメージのキャッシュクリア
docker system prune -a
```

## サポート情報

### デバッグモードの有効化
```bash
# 開発時の詳細ログ
DEBUG=* npm run dev

# Dockerコンテナの詳細ログ
docker compose logs -f --tail=100 portfolio-frontend
```

### 問題報告時の情報

問題が解決しない場合は、以下の情報を収集してください：

- Node.js バージョン (`node --version`)
- npm バージョン (`npm --version`)
- OS情報
- エラーメッセージの全文
- 問題が発生する手順
- ブラウザの開発者ツールのConsole出力
- Network タブのエラー詳細

### 関連ドキュメント

- [Astro公式ドキュメント](https://docs.astro.build/)
- [Tailwind CSS公式ドキュメント](https://tailwindcss.com/docs)
- [microCMS公式ドキュメント](https://document.microcms.io/)
- [Docker公式ドキュメント](https://docs.docker.com/)