# 安定版の記録 / Stable Version Record

イメージタグは JST の `YYYYMMDD-HHMM` です。ロールバック時はここを見て戻す先を選びます。実際に稼働中のタグは VPS で確認できます。

```bash
docker inspect --format='{{.Config.Image}}' portfolio-frontend
```

タグの一覧は
[GHCR のパッケージ画面](https://github.com/torifo/portfolio-astro/pkgs/container/portfolio-astro)
と、Actions の各実行のジョブサマリーにあります。

## 記録

### 20260908-0902

`main@78f4f42`「AdSense タグと ads.txt を追加」。
Journey × Instagram 連携を入れる直前の状態で、**戻すならここ**。

```bash
cd /home/ubuntu/Web/portfolio-astro && ./deploy.sh 20260908-0902
```

### 20251217-2041

テーマ切り替えの信頼性とパフォーマンスを直した版。localStorage での永続化、
API応答の24時間キャッシュ、初期化を `DOMContentLoaded` へ変更、チェック間隔を
30分→1分に短縮、初期テーマの即時適用によるフラッシュ防止。モバイル／タブレットでもテーマ設定を保存するようにした。あわせて手動モード時の日の出・日没時刻の表示を修正した。

古い版のため、いま戻す先としては推奨しません。

## 戻したあとにやること

ロールバックはイメージを戻すだけで、リポジトリは変わりません。原因を直して
`main` に push すれば、また新しいタグで本番が入れ替わります。
