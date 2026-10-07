# トラブルシューティング

このドキュメントでは、Astro製ポートフォリオサイトの開発・デプロイ時に発生する可能性がある問題とその解決方法について説明します。

## 目次

- [開発環境の問題](#開発環境の問題)
- [ビルド時の問題](#ビルド時の問題)
- [Docker関連の問題](#docker関連の問題)
- [API関連の問題](#api関連の問題)
- [コンポーネントの問題](#コンポーネントの問題)
- [テーマ機能の問題](#テーマ機能の問題)
- [Journey（Instagram 同期）の問題](#journeyinstagram-同期の問題)

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

**症状**: microCMS で直した内容がサイトに出ない

microCMS は**ビルドの前に** `scripts/ingest/fetch_microcms.mjs` が取得して `data/microcms/*.json` に置き、
ビルドはそのファイルを読むだけです（ブラウザからは呼びません）。取得に失敗した分は前回の
ファイルが残るので、サイトは壊れずに古い内容のまま出ます。

**解決方法**:
```bash
node scripts/ingest/fetch_microcms.mjs
# 「据置  skills: HTTP 401」→ API キーが無効。手元の .env のキーが古い可能性がある
#   （本番は GitHub Secrets のキーを使うので、手元だけ 401 でもデプロイは通る）
# 「据置  …: HTTP 404」→ PUBLIC_MICROCMS_SERVICE_DOMAIN が違う
```

microCMS の変更を本番に出すには、デプロイを走らせる必要があります（microCMS を直しただけでは
変わりません）。`gh workflow run "Deploy to Production" --ref main`

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

## コンポーネントの問題

### OpusSection - モバイル端末での開閉機能が動作しない

**症状**: 関連プロジェクトの開閉ボタンをクリックしても反応がない

**原因**:
動的に生成されたIDを含むCSSクラスセレクタが正しく動作しない問題が発生しました。
```javascript
// 動作しないコード例
const container = document.querySelector('.related-projects-' + projectId);
// projectId = "mocnp48jpl81" の場合
// document.querySelector('.related-projects-mocnp48jpl81') は null を返す
```

ハイフンを含む複雑な動的クラス名は、JavaScriptの`querySelector()`で信頼性の低い動作を引き起こします。

**解決方法**:
CSSクラスセレクタの代わりに**data属性セレクタ**を使用します。

```astro
<!-- 修正前（動作しない） -->
<div class="related-projects-{project.id}">...</div>
<script>
const container = document.querySelector('.related-projects-' + projectId);
</script>

<!-- 修正後（動作する） -->
<div data-related-container={project.id}>...</div>
<script is:inline>
const container = document.querySelector('[data-related-container="' + projectId + '"]');
</script>
```

**重要なポイント**:

1. **data属性を使用**:
   - `class="related-projects-{id}"` → `data-related-container={id}`
   - `class="related-toggle-icon-{id}"` → `data-related-icon={id}`

2. **属性セレクタ構文**:
   ```javascript
   // クラスセレクタ（推奨されない）
   document.querySelector('.related-projects-' + projectId)

   // 属性セレクタ（推奨）
   document.querySelector('[data-related-container="' + projectId + '"]')
   ```

3. **`is:inline`ディレクティブの追加**:
   ```astro
   <script is:inline>
   // TypeScript処理をスキップしてプレーンなJavaScriptとして実行
   </script>
   ```

**関連エラー**: SVGパスエラー
```
Error: <path> attribute d: Expected arc flag ('0' or '1')
```
このエラーはテンプレートリテラルとTypeScriptがJSX内のインラインイベントハンドラで競合した場合に発生します。`is:inline`ディレクティブを使用してプレーンJavaScriptに変更することで解決します。

**関連ファイル**:
- `/src/components/sections/OpusSection.astro` - 302-365行目（JavaScript実装）
- 188-198行目（data属性を使用したHTML）

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

### ライトモードで色が一色になる・白い文字が黒くなる

**症状**: 夜は色分けされているのに、昼（ライトモード）だけ背景のグラデーションが全部同じ紫になる。
白いはずの文字が黒くなる

**原因**: `src/styles/global.css` が `body.light-mode` の下で、次のクラスを `!important` で塗り替えている。

- `.bg-gradient-to-r` → 一律で cyan→violet のグラデーション（本来はボタン向け）
- `.text-white` `.text-white/70` など → 暗い灰色
- `.glass` → 白っぽい半透明

**解決方法**: 昼も夜も同じ色にしたい要素では、塗り替えの対象にならないクラスを使う。

- グラデーションは Tailwind v4 の `bg-linear-to-r`（`bg-gradient-to-r` と同じ見た目で、塗り替えの対象外）
- 白い文字は `text-slate-50`
- 地方グリッドのヘッダーと海外の枠はこの方法で書いている（`JourneySection.astro`）

```javascript
// 計算後の色をモード別に確かめる
document.body.classList.add('light-mode');
getComputedStyle(el).backgroundImage;
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

## Journey（Instagram 同期）の問題

同期は GitHub Actions の「Journey sync」が毎日2:47（JST）に回し（GitHub の定時は2〜3時間遅れることがある）、新着があれば PR を作ります。
仕組みは [DEPLOYMENT.md](../deployment/DEPLOYMENT.md) と
[設計書の 2026-09-29・2026-10-04 改訂](../superpowers/specs/2026-09-11-journey-instagram-design.md) を参照。

### 同期の PR ができない

- **未マージの同期 PR がある**: 新しい PR は作らずに見送る（手で直している最中を上書きしないため）。
  先の PR をマージするか閉じると、次の実行で新着をまとめて拾う。場所を書いた投稿の自動マージも
  その間は止まるので、開いた同期 PR は早めにマージするか閉じる
- **新着が無い**: Actions の実行のサマリーに「新着なし」と出る
- **自動でマージ済み**: 新着がすべて日付の後ろに場所を書いた投稿で、要確認が0件なら PR はすぐマージされ、
  開いた PR は残らない（Pull requests の Closed にある）。サマリーに「…PR を作ってマージする」と出る
- **PR が2つできた**: 場所を書いた投稿と書いていない投稿が混ざると、書いた側をマージ済みの PR、
  残りを `journey/sync-日付-hold` の開いた PR に分ける。開いた方の本文の件数の下に、マージ済みの PR 番号が出る
- **「保留の投稿を取り込み直せなかった」**: 分けたあとの取り込み直しで、保留の投稿を API から拾えなかった
  （新着が100件を超える日に起こりうる）。Actions の「Journey sync」→ Run workflow でもう一度回す。
  取り込みは既知の投稿だけのページで止まるので、それでも拾えなければ手元で
  `python3 scripts/ingest/sync_instagram.py --all` → `npm run journey:build` して PR にする
- 失敗していれば Actions の実行ログの赤いステップを見る。自動マージで止まったなら `GHCR_TOKEN` の権限を見る

### トークンが失効した（code 190）

60日で失効する。毎回延命しているので通常は起きないが、定時実行が長く止まっていると起きる。
Meta for Developers でアプリ `torifo-journey` のユースケース（Instagram）を開き、
API のセットアップ画面（URL に `selected_tab=API-Setup`）でトークンを生成し直して、secret を更新する。

```bash
gh secret set INSTAGRAM_ACCESS_TOKEN   # 値は貼り付け（画面に残さない）
```

### Instagram API がアクセスを拒否する（code 200）

トークンではなくアプリ側の問題。Meta for Developers の「必要なアクション」とアプリの
アラートを確認する。2026-09 には本人確認を済ませたら解消した。

### 毎日の同期が止まった

公開リポジトリの定時実行は、60日間コミットが無いと GitHub が自動で止める。止まる前にメールが届く。
Actions の「Journey sync」を開き、「Enable workflow」で再開する。手動実行（Run workflow）は
止まっていても使える。

### 「GHCR_TOKEN では secret を書き戻せない」

延長したトークンを secret に書き戻すのに `GHCR_TOKEN` を使っている。このトークンが secret を
書き換えられないと止まる。GitHub の Settings → Developer settings → Personal access tokens で、
`GHCR_TOKEN` に使っているトークンの権限を足す。

- classic トークン: scope に `repo` を足す（トークンの値は変わらないので secret はそのまま）
- fine-grained トークン: このリポジトリの「Secrets」を Read and write にする

### 県・撮影日が違う

PR のブランチで次のファイルを直し、`npm run journey:build` してコミットする。
Instagram 側のキャプションを直しても、同期では取り込み済みの投稿に届かない（`npm run journey:refresh` で読み直す）。

| 直したいもの | ファイル |
|---|---|
| 県 | `data/journey/overrides.json`（投稿ID またはタグ。`[]` はどの県にも入れない） |
| 撮影日 | `data/journey/date_overrides.json`（投稿ID。`"2023-09-05"`、月まで `"2023-09"`、年まで `"2022"`、分からなければ `"unknown"`） |

Instagram API は位置情報を返さないので、新着の県は本文とタグの文字だけで決まる。
投稿のときに日付と同じ行へ場所を書くと、それを最優先で使う（2026-09-30 以降の投稿）。

```
2025-06-28 横浜
東海汽船 東京湾クルーズ
#八景島シーパラ東京湾クルーズ東京タワーてんこ盛り旅
```

サイトに載せたくない投稿（旅と関係ない趣味など）は、場所の代わりに「趣味」と書く（`2025-10-04 趣味`）。
記録には残すが、県・旅・テーマ・件数のどこにも出さず、同期 PR は自動マージする。

読めなかったときは PR の要確認に「日付の後ろの場所を読めない」と出る。判定のルールを変えたら
`python3 scripts/journey/eval_resolve.py` で精度の前後を比べる（`--save` → 変更 → `--compare`）。

手元で直すときは、撮影地の座標（`data/journey/gps.json`、Git に入っていない）がある環境で
`journey:build` を流す。PR のブランチを別の作業ツリーに出すなら、`gps.json` と
`data/ontology/places.json` をそこへリンクしてから流す。

### 聖地巡礼の投稿が「作品名なし」に入った

聖地巡礼の作品は `data/journey/pilgrimages.json` の `works` を辞書にして決める。投稿のタグに作品名か別名が
無いと「作品名なし」にまとまる（同期 PR の本文の「聖地巡礼」に出る）。作品なら `works` に1件足して
`npm run journey:build` する。

```json
{"slug": "hyouka", "title": "氷菓", "aliases": ["別の呼び方"]}
```

聖地巡礼に数えるのは「聖地」を含むタグが投稿に付いているものだけで、旅の名前のタグ（…旅・…編）だけでは
数えない。作品のページから外れた旅の途中の投稿は、旅と県のページには今までどおり出る。

旅の名前に「巡礼」を入れても（「…WILLERの巡礼旅」）、それだけでは聖地巡礼に数えない。聖地巡礼に出したい
投稿には、聖地巡礼タグと作品名のタグを付ける（取り込み済みの投稿なら `npm run journey:refresh` で読み直す）。

タグを付け直さずに入れるなら、作品に次のどちらかを書く。どちらも聖地巡礼タグがなくてもその作品に入る。

- `"spots": ["伊勢志摩スカイライン"]`：聖地の場所のタグ。そのタグの投稿がすべて入る（弱虫ペダル）
- `"extraPostIds": ["投稿ID"]`：個別の投稿。本文に「〇〇聖地巡礼」と書かれていてタグを付けていない投稿など

### 旅の背景画像を足す・差し替える

旅のカード（旅の一覧・県のページ）と旅のページの見出しの背景は、本人が用意した画像。元の画像はリポジトリの外の
`~/dev/data/trip-covers/` に、旅の URL 名（`2025-07-miyagi.png` など。jpg・png・heic・webp）で置く。
同じフォルダの `README.md` に、旅の一覧と届いたかの印がある。

置いたら `npm run journey:covers` を流してコミットする。位置情報などの EXIF を消した webp（800w・1600w）が
`public/journey/trips/` にでき、一覧が `data/journey/trip_covers.json` に入る。差し替えは同じ名前で置き直して流す
（元の画像が新しいときだけ作り直す。`--force` で全部作り直す）。

- 画像がない旅は、その旅のいちばん早い投稿のサムネで出る
- 元の画像を消しても、サイトの画像は自動では消えない。消すときは `public/journey/trips/<slug>-*.webp` と
  `trip_covers.json` の該当行を手で消す
- 旅の名前のタグを付け直したときは slug を引き継ぐ（`trips.json` の tag・title を書き換える）ので、画像もそのまま使える

### Instagram でキャプション・タグを直した

同期は新着しか読み込まないため、取り込み済みの投稿には反映されない。`npm run journey:refresh` で全ページを読み直し、
キャプションが変わった投稿の本文とタグを書き換えてから `journey:build` まで流す。人が指定した撮影日・県はそのまま。

旅の名前のタグを付け直すと、旅の URL（slug）が変わる。読み直す前に `data/journey/trips.json` の該当する旅の
`tag`（名前をタグのままにしているなら `title` も）を新しいタグに書き換えておくと、今の slug を引き継げる。

日付の後ろの場所（`2025-06-28 横浜`）は、2026-09-30 以降に投稿したものだけが読まれる（投稿日で決まる）。
それより前の投稿のキャプションに場所を書き足しても、県は変わらない。県を直すなら `overrides.json` で。
API が本文を空で返した投稿は上書きせずに飛ばし、一覧に出す。

### プロフィールの投稿数とサイトの件数が1件ずれる

「フィードにも共有」をオフにしたリールは、プロフィールの投稿数に入らないが API では取れる。
2023-07-18 のリール「たまたま撮った桜道」がこれに当たる。取り込みの誤りではない。

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