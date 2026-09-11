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
       ├─ .env を作る        Secrets から PUBLIC_MICROCMS_* を書き出す
       │                     （Astro は PUBLIC_* をビルド時に静的出力へ埋め込むため、
       │                       Dockerfile の builder 段階で必要）
       ├─ docker build       ghcr.io/torifo/portfolio-astro に :タグ と :latest
       ├─ docker push        両方のタグを GHCR へ
       └─ VPS へ SSH         cd /home/ubuntu/Web/portfolio-astro && ./deploy.sh タグ
                               └─ docker compose pull → down → up -d → 起動確認
```

`deploy.sh` と `docker-compose.yml` は VPS 上の
`/home/ubuntu/Web/portfolio-astro/` にあり、リポジトリ内のものと同じ内容です。
**Actions はそこで `git pull` しません。** イメージを差し替えるだけなので、
VPS 上のチェックアウトが古くても動作に影響はありません。

## 必要な GitHub Secrets

| 名前 | 用途 |
|---|---|
| `GHCR_TOKEN` | GHCR への push |
| `VPS_HOST` / `VPS_USER` / `VPS_SSH_KEY` | VPS への SSH |
| `PUBLIC_MICROCMS_API_KEY` | ビルド時の microCMS 取得 |
| `PUBLIC_MICROCMS_SERVICE_DOMAIN` | 同上 |

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

デプロイのたびに日付タグが増えます。Journey のサムネ 1,013枚を含むため、イメージは約115MBあります（サムネを入れる前は約70MB）。VPS のストレージは有限なので、古いタグはときどき整理してください（稼働中のイメージは消さないこと）。

```bash
docker images ghcr.io/torifo/portfolio-astro --format '{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'
docker inspect --format='{{.Config.Image}}' portfolio-frontend   # 稼働中のタグ
```

## 履歴

以前は WSL でビルドして `deploy/docker-setup` ブランチを経由する手作業でしたが、
`b0ce778`「本番デプロイをActionsで完結させる」で自動化されました。
`deploy/docker-setup` ブランチは現役ではありません。
