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

- **フレームワーク**: Astro 7.4 (SSG) - 静的サイト生成による高速配信
- **スタイリング**: Tailwind CSS 4.3（`@tailwindcss/vite`） - ユーティリティファーストのCSS
- **言語**: TypeScript - 型安全性とコード品質の向上
- **ランタイム**: Node.js 22（ビルドと CI。Astro 7.4 は 22.22 以上が要る）
- **CMS**: microCMS - ヘッドレスCMSによるコンテンツ管理（Profile・Opus・Skills・Games API）
- **外部API**: Sunrise Sunset API - 日の出・日没時刻による自動テーマ切り替え
- **コンテナ化**: Docker (multi-stage build: node:22-alpine → nginx:alpine)

版は 2026-11-09 時点（`package.json`・`Dockerfile`）。
- **Webサーバー**: Nginx - 高速な静的ファイル配信
- **レジストリ**: GitHub Container Registry (GHCR)

### ✨ 特徴

- **レスポンシブデザイン**: モバイルからデスクトップまで対応
- **高速パフォーマンス**: Astro SSG による最適化された静的サイト
- **モダンUI**: グラデーションエフェクトとアニメーション
- **動的コンテンツ**: microCMS のデータ（Profile・Opus・Skills・Games）をデプロイ前に `data/microcms/*.json` へ取得し、ビルドはそれを読むだけ（ビルド中に microCMS を呼ばない）。microCMS の画像は表示の大きさの webp に縮小して取り、トップでは遅延読み込みにする
- **動的ルーティング**: `getStaticPaths()` による Opus 詳細ページ自動生成
- **カテゴリ/タグフィルター**: OpusSection・AboutSection でのクライアント側絞り込み
- **スキルタグ連携**: Opusの各サービスにスキルタグを表示、クリックでSkillsセクションへスムーズスクロール
- **スキル自動ソート**: レベル降順・作成日昇順でカテゴリ内を自動整列（固定カテゴリ順）
- **自動テーマ切り替え**: 日の出・日没時刻に基づくライト/ダークモード（JSTキャッシュ管理）。メニューで手動で選んだモードは、次の日の出か日没まで続いて自動に戻る
- **リアルタイム時計**: ヘッダーにJST時刻をリアルタイム表示
- **ビルド時刻表示**: フッターにビルド日時を自動埋め込み（JST）
- **Journey（Instagram 連携）**: 旅の写真を都道府県・旅・聖地巡礼・テーマの4つの軸で閲覧。新着は毎日 GitHub Actions が取り込んで PR にし、本文の日付の後ろに場所を書いた投稿は自動でマージする
- **Journey の県のページ**: 「投稿した場所」の地図（県の形の上に、近い市区町村をまとめたエリアを投稿の多さで塗る。押すと下の投稿の一覧をそのエリアに絞る）・よく付けたタグのハイライト・日付の行に書いたエリア（`北海道(旭川)`）
- **Journey の旅・聖地巡礼のページ**: 旅の見出しを押すと背景画像だけを開く。作品のページは期ごとの公式 PV と公式サイトをサムネで並べ、収まらなければ流れる帯にする。旅の旧 URL は新 URL へ転送する

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
│   │   ├── sections/
│   │   │   ├── HeroSection.astro     # メインビジュアル（Profile API連携）
│   │   │   ├── AboutSection.astro    # 自己紹介・経歴タイムライン（Profile API連携・タグフィルター）
│   │   │   ├── SkillsSection.astro   # 技術スキル（Skills API・固定カテゴリ順・レベルソート・アンカーID）
│   │   │   ├── OpusSection.astro     # 作品・プロジェクト（Opus API・カテゴリフィルター・スキルタグ）
│   │   │   ├── JourneySection.astro  # 日本8地方・都道府県別旅記録（旅・聖地巡礼・テーマへの入口）
│   │   │   └── GamesSection.astro    # ゲーム関連（Games API連携）
│   │   └── journey/
│   │       ├── PostGrid.astro           # 投稿サムネ一覧（県・旅・聖地巡礼・テーマで共用）
│   │       ├── PrefectureHeatmap.astro  # 県のページの「投稿した場所」の地図
│   │       ├── TripCard.astro           # 旅のカード（背景画像つき）
│   │       ├── CoverHero.astro          # 旅・作品のページの見出し（背景画像・旅は押すと画像だけを開く）
│   │       ├── WorkBand.astro           # 聖地巡礼の一覧の作品の帯
│   │       ├── OfficialEmbeds.astro     # 作品のページの公式 PV・公式サイト
│   │       ├── ReelStrip.astro          # PV・公式サイトのサムネの並び（収まらなければ流れる帯）
│   │       └── PrefectureChips.astro    # 県の名前のチップ（訪問済みの県だけリンク）
│   ├── lib/
│   │   ├── microcms.ts           # microCMS のデータ読み出し（data/microcms/*.json を読む・型定義・cmsImage()・SKILL_CATEGORY_SLUG）
│   │   ├── journey.ts            # Journey のビルド時データ読み出し（外部サービスを呼ばない）
│   │   ├── reel.ts               # 流れる帯の動き（トップの旅の帯・作品のページの PV で共用）
│   │   ├── prefecture-maps.json  # 県の形とエリア（build_municipality_maps.py が作る）
│   │   └── region-silhouettes.json  # 地方のシルエット（build_region_silhouettes.py が作る）
│   ├── layouts/
│   │   └── Layout.astro          # 基本レイアウト
│   ├── pages/
│   │   ├── index.astro           # メインページ
│   │   ├── contact.astro         # お問い合わせ
│   │   ├── 404.astro / privacy-policy.astro / terms.astro
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
│   ├── journey/thumbs/           # 投稿サムネ 1,283枚（2026-11-09 時点。480px webp・自前保存）
│   ├── journey/trips/            # 旅の背景画像（webp）
│   └── journey/works/            # 聖地巡礼の作品の背景画像（webp）
├── data/
│   ├── microcms/                 # microCMS の取得結果（デプロイ時に CI が上書きしてコミット）
│   ├── ontology/                 # 地名オントロジーと県境ポリゴン（機械生成・候補源）
│   └── journey/                  # 投稿・判定結果・辞書・旅・聖地巡礼・テーマ・投稿の市区町村とエリアの中心
├── scripts/
│   ├── ontology/                 # オントロジーと県境データの生成
│   ├── ingest/                   # エクスポート取り込み・API増分取り込み・サムネ生成・permalink取得・microCMS の取得
│   └── journey/                  # 都道府県の解決・旅/聖地巡礼/テーマの抽出・背景画像・地図・同期 PR
├── .github/workflows/            # GitHub Actions設定（main への push で本番デプロイ・毎日の Journey 同期）
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
- API はデプロイの前段（`scripts/ingest/fetch_microcms.mjs`）でだけ呼び、結果を `data/microcms/*.json` に置く。ビルドはそのファイルを読むだけ → APIキーは最終HTMLに含まれない。取得に失敗した分はコミット済みの前回分が残る

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
2025-06-28 横浜        … 神奈川県（「横浜➝東京」なら先頭の横浜）。書いた県なら、訪問済みでなくても最初の投稿でも自動マージ
2025-09-13 北海道(旭川) … 北海道。括弧の中は県のページの県名の下に「エリア」として出る（多い順）
2025-10-04 趣味        … サイトに載せない（記録には残す）
```

PR の「要確認」は、本番で実際に起きた誤りの型を機械で探したもの
（旅タグの語で県が決まった、初めての県、同じ日の投稿と県が違う、旅の期間外、撮影日が不明、作品のページが無い、など）。
日付の後ろに書いた県には「初めての県」を出さない。訪問済み（`prefectures.json` の `visited`）は観光したかで決め、通っただけの県は付けない。
直すときは PR のブランチで次のファイルを直し、`npm run journey:build` してコミットする。

| 直したいもの | ファイル | 書き方 |
|---|---|---|
| 県 | `data/journey/overrides.json` | `"投稿ID": ["13"]` または `"タグ": ["14"]`（タグならそのタグの投稿すべてに効く）。`[]` はどの県にも入れない（複数の場所の寄せ集めなど） |
| 撮影日 | `data/journey/date_overrides.json` | `"投稿ID": "2023-09-05"`。月までなら `"2023-09"`、年までなら `"2022"`、分からなければ `"unknown"`（「日付不明」と出る） |
| テーマ | `data/journey/themes.json` の `extraPostIds` | `["投稿ID"]`（タグの無い投稿をテーマに入れる） |
| 再利用できる地名 | `data/journey/gazetteer.json` | `"地名": ["27"]` |
| 離島の辞書 | `data/journey/islands.json`（作るもの） | 直接書かない。`scripts/journey/build_islands.py` の人の一覧（`EXTRA`）に島を足すか、外す名前（`AMBIGUOUS`）に足して `npm run journey:islands`。`gazetteer.json` の語が勝つ |
| 聖地巡礼の作品 | `data/journey/pilgrimages.json` の `works` | `{"slug": "hyouka", "title": "氷菓", "aliases": []}`（タグに作品名か別名があればその作品に入る）。聖地の場所のタグは `"spots"`、個別の投稿は `"extraPostIds"` に書くと、聖地巡礼タグがなくても入る。聖地巡礼タグがあって作品のタグが無い投稿は、同じ日（無ければ同じ旅）の投稿の作品が1つならその作品に入る。2つ以上なら「作品が複数」で同期 PR が止まるので、`extraPostIds` で決める。作品名をサイトに出したくない作品は `"hidden": true`（作品のページを作らず、投稿は旅と県のページにだけ出る） |
| 旅の背景画像 | `~/dev/data/trip-covers/<slug>.<拡張子>`（リポジトリの外。slug は旅の開始日 `2025-08-31`） | 置いてから `npm run journey:covers`。EXIF を消した webp（800w・1600w）が `public/journey/trips/` にでき、一覧が `data/journey/trip_covers.json` に入る。画像がない旅は投稿のサムネで出る |
| 聖地巡礼の作品の背景画像 | `~/dev/data/work-covers/<slug>.<拡張子>`（リポジトリの外）と同じフォルダの `meta.json` | 置いてから `npm run journey:work-covers`。`meta.json` には作品ごとに `credit`（他人の写真の出典の表示）・`source`（出典のページ）・`mode`（一覧の帯で `cover`＝切り取る／`fit`＝全体を見せる）・`focus`（切り取る中心）を書く。風景の写真だけの版は `~/dev/data/work-covers/_landscape/` にあり、`npm run journey:work-covers -- --source ~/dev/data/work-covers/_landscape --force` で戻せる |
| 聖地巡礼の公式リンク | `data/journey/work_links.json` | 作品ごとに公式の PV（YouTube の id・題・チャンネル）・公式サイト（`officialSite`）・カード（`site` の題と og:image の URL。og:image は公式サイトから直接出す）。作品のページに置く（画像はこちらに置かない）。公式 X は表示していない。シリーズのある作品は `series` に期ごと（放送順）の `label`（`2期（続）` など）・`year`・`kind`・`youtube`・`officialSite`・`siteImage`（サムネ。横長の共有用画像が無いサイトはその期の PV のコマ）を書く。TV は全期、TV 以外は聖地巡礼のモデル地があるものだけ、実写は入れない |
| 「投稿した場所」のエリアの中心 | `data/journey/area_hubs.json` | 県コードごとに `hubs`（中心にする市区町村名）と `radiusKm`（書かなければ県の大きさから決まる）。変えたら下の地図のスクリプトを流す |

Instagram 側のキャプションを直しても、同期（新着しか読まない）では取り込み済みの投稿に届かない。
直したら `npm run journey:refresh` で読み直す（下記）。

手元で回す場合:

```bash
# 新着だけを API から取り込む（トークンは環境変数か ~/dev/.env.dev）
npm run journey:sync

# Instagram 側で直したキャプション・タグを、取り込み済みの投稿に読み直す（新着は足さない）
npm run journey:refresh

# 同期 PR を手元から作る（別の作業ツリーで行うので手元は触らない）
bash scripts/journey/auto_sync.sh            # --dry-run で PR を作らない

# エクスポート zip から作り直す（EXIF の GPS が取れるのはこちらだけ）
python3 scripts/ingest/parse_export.py <エクスポートの展開先>
python3 scripts/ingest/build_thumbs.py
python3 scripts/ingest/fetch_permalinks.py
npm run journey:build

# 文字だけの県判定の精度を測る（判定の規則を変える前に --save、変えた後に --compare）
python3 scripts/journey/eval_resolve.py

# 県のページの「投稿した場所」の地図を作り直す（gps.json と N03 の市区町村 GeoJSON が要る。手元でだけ動く）
python3 scripts/journey/build_municipality_maps.py ~/dev/data/kokudo/N03-20260101.geojson   # --report で決まらない投稿を出す
```

撮影地の座標（`data/journey/gps.json`）は公開しないので Git に入れていない。Actions など
座標が無い環境では、GPS で決まった判定を前回の結果から引き継ぐ（座標がある環境と結果は同じ）。
**「投稿した場所」の地図だけは引き継がない。** 投稿 → 市区町村（`data/journey/post_municipalities.json`）と
県の形・エリア（`src/lib/prefecture-maps.json`）は上の `build_municipality_maps.py` が作り、同期にも
`journey:build` にも入っていないので、新しい投稿はこれを手元で流してコミットするまで地図に入らない。
座標の無い投稿は本文の地名・名所・短いタグから市区町村を引き、名所の座標が控え（`data/journey/place_coords.json`）に
無ければ Wikidata に問い合わせて控えを書き換える。N03 の市区町村 GeoJSON の用意は [data/ontology/README.md](data/ontology/README.md)。
仕組みの詳細は [設計書の 2026-09-29・2026-10-04 改訂](docs/superpowers/specs/2026-09-11-journey-instagram-design.md)、
[精度改善の設計](docs/superpowers/specs/2026-09-30-journey-accuracy-design.md)、
[PR の分割の設計](docs/superpowers/specs/2026-10-04-journey-sync-pr-split-design.md)、
[旅の背景画像の設計](docs/superpowers/specs/2026-10-08-journey-trip-covers-design.md)、
[旅の URL を開始日にする設計](docs/superpowers/specs/2026-10-18-journey-trip-date-slugs-design.md)、
[作品の期ごとの PV の設計](docs/superpowers/specs/2026-10-31-pilgrimage-series-pvs-design.md) にある。
決めたことと決めた人は [DECISIONS.md](docs/journey/DECISIONS.md)。

### ✅ 実装済み機能

- [x] microCMS Profile API連携（Hero・About・Connect）
- [x] microCMS Opus API連携（作品一覧・カテゴリフィルター）
- [x] microCMS Skills API連携（技術スキル一覧・8カテゴリ固定順・レベル降順ソート）
- [x] microCMS Games API連携（ゲーム情報・SNS）
- [x] Opus詳細ページ自動生成（`/opus/[slug]`）
- [x] About経歴タイムライン タグフィルター（Academic / Technology / Opus / Pulse / Community）
- [x] OpusのrelatedSkillタグ表示（カテゴリ別グループ・Skillsセクションへのアンカーリンク）
- [x] 日の出・日没APIによる自動テーマ切り替え（JSTの日付変わりでキャッシュ自動リセット・手動の選択は次の日の出か日没まで）
- [x] Journey 8地方・都道府県別訪問管理（「制覇した地方」は県をすべて訪れた地方の数・地方の形のシルエット・9枠目に海外）
- [x] Journey × Instagram 連携（投稿1,283件（2026-11-09 時点）・都道府県100%解決・LLM呼び出しなし）
- [x] 都道府県ページ自動生成（`/journey/[slug]`・訪問済み43県（2026-11-09 時点））
- [x] 県のページの「投稿した場所」の地図・ハイライト（よく付けたタグ）・日付の行に書いたエリア
- [x] 旅・聖地巡礼・テーマの各ページ（2026-11-09 時点で旅36件・聖地巡礼14作品・テーマ13。同じ投稿が複数ページに出る）
- [x] 旅の URL は開始日（`/journey/trips/2025-08-31/`）・旧 URL は新 URL へ転送・見出しを押すと背景画像だけを開く
- [x] 聖地巡礼の作品のページに期ごとの公式 PV と公式サイトのサムネ（収まらなければ流れる帯）
- [x] microCMS の画像を表示の大きさの webp に縮小して取得
- [x] 投稿サムネの自前保存（480px webp・Instagram の media URL 失効対策）
- [x] 新着の自動取り込み（毎日 GitHub Actions が PR を作る・手動実行も可）
- [x] 日付の後ろに場所を書いた投稿の自動マージ（混ざれば PR を分ける・「趣味」は載せない）
- [x] 文字だけの県判定の精度測定（`eval_resolve.py`・誤り 8.1%（2026-11-09 時点、正解のある 1,020件中83件））
- [x] 存在しない URL は 404 を返す（`404.astro`）・プライバシーポリシー・利用規約
- [x] Footerビルド時刻自動表示
- [x] GHCR Docker イメージ管理

---

## English

### 📖 Overview

A modern portfolio website built with Astro and TypeScript. Features microCMS API-driven dynamic content, automatic light/dark theme switching via Sunrise-Sunset API, and high-performance static generation with Astro SSG. Build and deployment environments are separated for efficient resource usage.

### 🛠️ Tech Stack

- **Framework**: Astro 7.4 (SSG) - Static site generation for fast delivery
- **Styling**: Tailwind CSS 4.3 (`@tailwindcss/vite`) - Utility-first CSS
- **Language**: TypeScript - Type safety and code quality
- **Runtime**: Node.js 22 for builds and CI (Astro 7.4 needs 22.22 or later)
- **CMS**: microCMS - Headless CMS (Profile, Opus, Skills & Games APIs)
- **External API**: Sunrise Sunset API - Auto theme switching
- **Containerization**: Docker (multi-stage: node:22-alpine → nginx:alpine)

Versions as of 2026-11-09 (`package.json`, `Dockerfile`).
- **Web Server**: Nginx - High-performance static file serving
- **Registry**: GitHub Container Registry (GHCR)

### ✨ Features

- **Responsive Design**: Optimized for mobile to desktop
- **High Performance**: Static site generation with Astro SSG
- **Dynamic Content**: microCMS content (Profile, Opus, Skills, Games) is fetched into `data/microcms/*.json` before the build, which only reads those files; microCMS images are requested as webp at their display size
- **Dynamic Routes**: Auto-generated Opus detail pages via `getStaticPaths()`
- **Filter UI**: Category/tag filters in Opus and About sections
- **Skill Tags in Opus**: Each Opus service displays linked skill tags grouped by category; clicking navigates to the corresponding Skills section with smooth scroll
- **Skill Sorting**: Skills auto-sorted by level (desc) then creation date (asc) within each fixed-order category
- **Auto Theme**: Light/dark mode based on Tokyo sunrise/sunset times (cache resets at JST midnight). A mode picked by hand lasts until the next sunrise or sunset, then returns to auto
- **Real-time Clock**: JST time in header
- **Build Timestamp**: Build date auto-embedded in footer
- **Journey (Instagram)**: Browse travel photos by prefecture, trip, anime pilgrimage and theme. GitHub Actions ingests new posts every morning and opens a pull request for review
- **Journey pages**: prefecture pages shade the areas where posts were made, list frequent tags and show the areas written on the date line; trip headers open the cover image on its own; pilgrimage work pages show each season's official PV and site as thumbnails (a flowing strip when they do not fit); old trip URLs forward to the new ones

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

The prefecture area map is not updated by the sync. `scripts/journey/build_municipality_maps.py` needs the
private `gps.json` and the N03 municipality GeoJSON, so new posts only appear on the map after it is run
locally and committed.

### 🔌 microCMS API

- **Base**: `https://portorifo.microcms.io/api/v1/`
- **Profile** (`/profile`): Name, title, introduction, avatar, emails, history timeline
- **Opus** (`/opus?orders=createdAt`): Works, categories, related links, thumbnails, skill tags (`relatedSkill`)
- **Skills** (`/skills`): Tech skills, categories, levels, icons, linked works (`usedIn`)
- **Games** (`/games`): Game info, related SNS, tags
- The API is called only by `scripts/ingest/fetch_microcms.mjs` before the build, which reads the saved `data/microcms/*.json` — API keys are never exposed to browsers
