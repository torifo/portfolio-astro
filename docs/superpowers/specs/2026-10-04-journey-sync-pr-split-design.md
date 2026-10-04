# Journey 同期PRのグループ表示と自動マージの分割 — 設計

- 日付: 2026-10-04
- 対象: `scripts/journey/sync_report.py`・新規 `scripts/journey/drop_posts.py`・新規 `scripts/journey/open_sync_prs.sh`・`.github/workflows/journey-sync.yml`
- 前提: [精度改善の設計](2026-09-30-journey-accuracy-design.md)（日付の後ろの場所・自動マージ）

## 背景

同期PR #6（新着17件）は、15件が日付の後ろに場所を書いた投稿（東京・宮城・福島）で、2件（2025-07-04 の
「揺れる紫陽花」「郷土の森博物館 散策」）は場所が無く、タグの「郷土の森博物館」で東京都に決まっていた。
1件でも場所の無い投稿が混ざると自動マージしない決まりなので、17件まとめて開いたまま止まった。
新着の表も17行が1枚に並び、旅ごとの見通しが悪かった。

## 1. 新着の表をグループごとにまとめる（sync_report.py）

- 「## 新着 N 件」の下を、グループごとの小見出し `### …` と表に分ける。表の列は今と同じ
- 旅のグループ: 新着が旅のタグ（`trips.json` の hidden でない旅の `tag`）を持っていればその旅に入れる。
  ほかの点検（旅の期間外・旅の主な県と不一致）と同じ見分け方。見出しは `### 旅名（期間・新着 N 件）`。
  期間は `trip_period()` と同じ書き方
- 旅に入らない投稿: 撮影日ごとにまとめ、見出しは `### 2025-07-04（旅に入らない投稿）`
- グループは中の新着の最も早い撮影日の順。グループ内は撮影日・投稿IDの順
- 「## 要確認」の表は今のまま1枚

## 2. 場所を書いた投稿と書いていない投稿が混ざったら、PR を分ける

### 対象と保留

- 自動マージの対象（auto）: 根拠が `date-line-place` で、要確認が1件も出ていない新着。
  日付の後ろに「趣味」と書いた投稿（`date-line-hidden`、サイトに載せない）も対象
- 保留（hold）: それ以外の新着（場所の無い投稿、場所はあるが「初めての県」「旅の期間外」などが出た投稿）。
  2026-10-04〜: 日付の後ろに書いた県が `data/journey/prefectures.json` で訪問済みなら「初めての県」は出さない
  （宮崎のように、行ったと決めてから初めて投稿する県を自動マージにするため。訪問済みでない県は今までどおり保留）
- `sync_report.py` は `--summary` に `autoIds`・`holdIds`（投稿IDの配列）を足す。`autoMerge` は
  「auto が1件以上で hold が0件」（今と同じ意味）

### 流れ（`open_sync_prs.sh`、ワークフローの「Open a pull request」の中身をここへ移す）

1. 取り込んだ全件をコミットし、全件で本文と summary を作る（今と同じ）
2. Actions のサマリーに「自動マージ N 件 / 保留 M 件」を出す。`DRY_RUN=true` ならここで終わる（push も PR もしない）
3. hold が0件: 今までどおり PR を作り、auto があれば `GHCR_TOKEN` でマージ
4. auto が0件: 今までどおり PR を作って開いたまま
5. 両方ある（分割）:
   1. `drop_posts.py` で hold の投稿を取り除き、`npm run journey:build` で組み直して、コミットを作り直す
      （メッセージは件数を auto に合わせる）
   2. 組み直した状態で本文と summary を作り直す。`autoMerge` が true でなければ分割をやめ、全件のコミットに
      戻して1つの PR（開いたまま）にする
   3. push → PR → `GHCR_TOKEN` で rebase マージしてブランチを消す（Deploy to Production が本番へ出す）
   4. `origin/main` を取り直し、そこから `${BRANCH}-hold` を作って `npm run journey:sync` をもう一度回す。
      main に hold の投稿は無いので、それだけが新着として入る（この間に別の新着が来ていれば一緒に入る）
   5. コミット → 本文（先頭に `--preface` で「日付の後ろに場所を書いた N 件は #A で自動マージした。」）→ push →
      PR を開いたまま残す
- 2つ同時に作らないのは、どちらも posts.json などに追記するので、先にマージした側と衝突するため
- hold の PR が開いている間は、次の定時実行は見送られる（今までどおり `journey/sync-` で始まるブランチ）
- 途中で失敗したら `set -e` でそのステップを失敗させる。マージは、GitHub がマージできるかを決めるまで（最大30秒）待ち、
  失敗したら15秒後に1回だけやり直す。それでも落ちたら A は開いたまま、hold の PR は作られない
- 取り込み直しで hold の投稿を拾えなかったら（既知の投稿だけのページで読むのをやめるため、新着が100件を超える日）、
  警告を出して終わる

### drop_posts.py

- `--ids`（カンマ区切り）の投稿を `data/journey/posts.json` と `data/journey/permalinks.json` から消し、
  `public/journey/thumbs/<id>.webp` を消す。ほかに投稿IDごとに作るファイルがあればそれも
- 書き出しの形式は取り込み（`scripts/ingest/sync_instagram.py`）と同じにして、消した投稿以外に差分を出さない
- 派生データ（resolved・trips・pilgrimages・themes）は触らない。呼び出し側が `npm run journey:build` で作り直す

## 確かめ方

- PR #6 の head（`origin/journey/sync-20261004-0514`）に当てて、新着の表が旅・日付ごとに分かれ、
  auto 15 件・hold 2 件になること
- 同じ状態で hold の2件を `drop_posts.py` で消して組み直すと、新着15件・要確認0件・`autoMerge` true になること
- `open_sync_prs.sh` を `DRY_RUN=true` で通すと、計画（自動マージ 15 件 / 保留 2 件）を出して push せずに終わること
- 実際の分割とマージは、PR #6 を閉じて同期を回し直して確かめる
