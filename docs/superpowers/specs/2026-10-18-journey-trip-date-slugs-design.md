# 旅の URL 名を開始日にする — 設計

- 日付: 2026-10-18
- 対象: `scripts/journey/build_trips.py`・新規 `data/journey/trip_redirects.json`・`astro.config.mjs`・旅の背景画像（`~/dev/data/trip-covers/`・`public/journey/trips/`・`data/journey/trip_covers.json`）
- 前提: [旅の背景画像の設計](2026-10-08-journey-trip-covers-design.md)

## 背景

旅の URL 名（slug）は「旅が始まった月＋投稿のいちばん多い県」（`2025-08-chiba`）だった。

- 同じ県の旅が並ぶと見分けがつかない。千葉が6件あり、うち3件がディズニー（2023-09・2025-02・2025-08）
- 名前は旅ができたときの1回だけ決まり、あとは引き継ぐ。その後に投稿が増えて主な県が変わっても直らない
  （小豆島・鳴門・祖谷の旅が `2025-07-tokyo`、山梨・長野のスキーのドライブが `2025-02-tokyo-2`）

本人の指示（2026-10-18）：「可能な限り自動で。毎回一意にグループ（旅のタグ）があって日付も被らないから、そこを上手く自動化して」。
形は開始日 `yyyy-mm-dd` に決めた（開始日＋終了日、開始日＋タグのローマ字も候補に出した）。

## 1. URL 名の決め方（build_trips.py）

- 旅の開始日（`start`）をそのまま URL 名にする（`2025-08-31`）。旅の日付は被らないので一意。
  同じ日に始まる旅が2つできたときだけ `-2`・`-3` を足す
- 今と同じく、一度決めた名前は `trips.json` に残して引き継ぐ（`--merge`）
- 引き継いだ名前を付け替えるのは次のとき。付け替えたら旧→新を `trip_redirects.json` に書き足す
  - 古い形（`yyyy-mm-県`）の名前（最初の付け替え）
  - 開始日の形だが、今の開始日と違う（前日の写真が後から投稿されて開始日が早まったなど）。
    ただし背景画像がある旅（`trip_covers.json` にある旅）は付け替えない。画像は投稿が終わってから入るので、
    その頃には日付は固まっている。画像のファイル名まで自動で付け替える仕組みは作らない
- タグを付け直して旅が作り直されても、開始日が同じなら同じ名前になる

## 2. 古い URL の転送

- `data/journey/trip_redirects.json` に `{"redirects": {"旧": "新"}}` で持つ。build_trips.py が書き足す
  - A→B→C は A→C にまとめる
  - 今ある旅の名前と同じ旧名は消す（ページの方を生かす）
- `astro.config.mjs` の `redirects` をこのファイルから作る。静的ビルドなので、旧 URL に新 URL へ飛ぶページ
  （meta refresh・canonical つき）ができる。nginx の 301 は付け替えのたびに設定を手で直すことになるので使わない

## 3. 最初の付け替え（1回だけ）

- `npm run journey:build` で36件が開始日の名前になり、旧→新が `trip_redirects.json` に入る
- 背景画像は使い捨てのスクリプトで付け替える
  - `~/dev/data/trip-covers/<旧>.<拡張子>` と `_gen/<旧>/`
  - `public/journey/trips/<旧>-{800,1600,fill}.webp`（`git mv`）
  - `trip_covers.json` のキー
- そのあと `npm run journey:covers` を流し、作り直しが0件で README の表が新しい名前になることを見る
- ドキュメント（README・TROUBLESHOOTING・DECISIONS）の URL 名の説明を直す

## 4. 確認

- ビルドして次を見る
  - 旅ページが36件、新しい名前で出る
  - 旧 URL 36件がそれぞれ正しい新 URL に飛ぶ
  - 背景画像35件が出る
  - 古い名前の画像・リンクが残っていない
- push してデプロイ後、本番を直接取って同じことを確かめる。観点ごとに並列で点検する
