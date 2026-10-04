# デプロイ手順 / Deployment

## 要点

**`main` に push すると本番が入れ替わります。** 承認の関門はありません。
GitHub Actions がビルドから VPS への反映まで一気に行います。

本番: https://portorifo.riumu.net

## 経路

```
main に push（または Actions から workflow_dispatch）
  │
  └─ .github/workflows/deploy.yml
       ├─ タグを作る         TZ=Asia/Tokyo date +%Y%m%d-%H%M   例: 20260908-0902
       ├─ microCMS を取得    scripts/ingest/fetch_microcms.mjs → data/microcms/*.json
       │                     失敗した分はコミット済みの前回分が残る
       ├─ docker build       ghcr.io/torifo/portfolio-astro に :タグ と :latest
       ├─ docker push        両方のタグを GHCR へ
       ├─ VPS へ SSH         cd /home/ubuntu/Web/portfolio-astro && ./deploy.sh タグ
       │                       └─ docker compose pull → down → up -d → 起動確認
       └─ キャッシュを commit 取得した data/microcms/*.json を main に戻す
                             （data/microcms/** は paths-ignore なので再発火しない）
```

配信は nginx（`nginx.conf`）。**存在しない URL には 404 を返し、`404.astro` を表示します。**
以前はどの URL にもトップを 200 で返していたため、リンク切れに気づけませんでした。

`deploy.sh` と `docker-compose.yml` は VPS 上の
`/home/ubuntu/Web/portfolio-astro/` にあり、リポジトリ内のものと同じ内容です。
**Actions はそこで `git pull` しません。** イメージを差し替えるだけなので、
VPS 上のチェックアウトが古くても動作に影響はありません。

## 必要な GitHub Secrets

| 名前 | 用途 |
|---|---|
| `GHCR_TOKEN` | GHCR への push。Journey 同期では延長した Instagram トークンを secret に書き戻すのにも使う（repo 権限が要る） |
| `VPS_HOST` / `VPS_USER` / `VPS_SSH_KEY` | VPS への SSH |
| `PUBLIC_MICROCMS_API_KEY` | ビルド時の microCMS 取得 |
| `PUBLIC_MICROCMS_SERVICE_DOMAIN` | 同上 |
| `INSTAGRAM_ACCESS_TOKEN` | Journey 同期。実行のたびに延長されて書き換わる |

リポジトリ設定 **Settings → Actions → General →「Allow GitHub Actions to create and approve pull requests」はオン**
にしてあります（Journey 同期が PR を作るため）。

## Journey の同期（Instagram → PR）

```
毎日 2:47 JST（cron: 47 17 * * *。GitHub の定時は2〜3時間遅れる）/ Actions の「Journey sync」→ Run workflow
  │
  └─ .github/workflows/journey-sync.yml
       ├─ 未マージの同期 PR（journey/sync-*）があれば見送る
       ├─ Instagram トークンを延命 → secret INSTAGRAM_ACCESS_TOKEN に書き戻す
       ├─ npm run journey:sync            新着の取り込み・判定・旅/聖地巡礼/テーマの再生成
       ├─ 新着が無ければ終わり
       └─ scripts/journey/open_sync_prs.sh   commit → push → PR（本文は scripts/journey/sync_report.py）
            ├─ 新着がすべて「日付の後ろの場所」で要確認0件 → GHCR_TOKEN でマージまでする
            ├─ 場所の無い投稿・要確認が出た投稿だけ → PR を開いたまま
            └─ 両方が混ざる → 場所を書いた投稿だけの PR を作ってマージし、
                 その main から取り込み直して残りを journey/sync-日付-hold の PR（開いたまま）にする
```

**PR をマージすると、main への push として上の本番デプロイが走ります。** PR を作った時点では
何も公開されません。直すときは PR のブランチで `data/journey/overrides.json` などを直して push
してからマージします。

本文の日付と同じ行に場所を書いた投稿（`2025-06-28 横浜`）で点検に何も出なかったものと、
載せない印に「趣味」と書いた投稿（`2025-10-04 趣味`。サイトのどこにも出さない）は、
人が見る点が無いので自動でマージします。マージに `GITHUB_TOKEN` を使うと、その push では
本番デプロイが起動しない（GitHub の仕様）ため、secret の書き戻しと同じ `GHCR_TOKEN` を使います。
書いた県が訪問済み（`data/journey/prefectures.json`）なら、その県の最初の投稿でも止めません。
場所の書いていない投稿や要確認が出た投稿は PR で止まります。両方が一度に来たときは PR を2つに
分け、先に自動マージ側を入れてから残りの PR を作ります（同時に作ると posts.json などで衝突するため）。
PR の新着の表は、旅ごと・旅に入らない投稿は撮影日ごとの小見出しに分けて並べます。

- 手動実行の入力 `dry_run` を付けると、PR を作らず本文だけを Actions のサマリーに出す
  （トークンも延命しない）。`base` に古いコミットを渡すと、そこから新着がある状態を再現できる。
  古い `base` で `dry_run` を外すと、古いデータの PR ができてマージで巻き戻るので必ず付けること
- Actions には撮影地の座標（`gps.json`、公開しない）が無い。GPS で決まった判定は前回の結果を引き継ぐ
- サムネイル変換のため、実行のたびに ImageMagick と ffmpeg を apt で入れる
- **公開リポジトリの定時実行は、60日間コミットが無いと GitHub が自動で止めます。** 止まる前にメールが来て、
  Actions の「Journey sync」から再開できます（手動実行は止まっていても使えます）

手元から同じことをするなら `bash scripts/journey/auto_sync.sh`（`--dry-run` あり）。
別の作業ツリーで行うので、手元の変更には触りません。

## 手元での確認

push 前に、CI と同じ経路で作ったイメージを確かめられます。**ワーキングツリーではなく git の中身からビルドする**のが要点で、これで追跡漏れを検出できます。

```bash
rm -rf /tmp/ci_sim && mkdir -p /tmp/ci_sim
git archive <ブランチ> | tar -x -C /tmp/ci_sim
cp .env /tmp/ci_sim/.env
cd /tmp/ci_sim && docker build -t portfolio-ci-test:local .

docker run -d --name pf-test -p 8099:80 portfolio-ci-test:local
curl -I http://localhost:8099/
docker rm -f pf-test
```

## ロールバック

```bash
ssh <VPS>
cd /home/ubuntu/Web/portfolio-astro
./deploy.sh <戻したいタグ>
```

タグの一覧は
[GHCR のパッケージ画面](https://github.com/torifo/portfolio-astro/pkgs/container/portfolio-astro)
か、Actions の各実行のジョブサマリーで確認できます。

## イメージ容量に注意

デプロイのたびに日付タグが増えます。Journey のサムネ（1,000枚超）を含むため、イメージは約115MBあります（サムネを入れる前は約70MB）。VPS のストレージは有限なので、古いタグはときどき整理してください（稼働中のイメージは消さないこと）。

```bash
docker images ghcr.io/torifo/portfolio-astro --format '{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'
docker inspect --format='{{.Config.Image}}' portfolio-frontend   # 稼働中のタグ
```

## 履歴

以前は WSL でビルドして `deploy/docker-setup` ブランチを経由する手作業でしたが、
`b0ce778`「本番デプロイをActionsで完結させる」で自動化されました。
`deploy/docker-setup` ブランチは現役ではありません。
