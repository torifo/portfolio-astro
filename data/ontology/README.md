# オントロジーと境界データ

Journey（Instagram 連携）の都道府県判定に使う参照データ。いずれも生成物であり、
再生成の手順をここに残す。**確定辞書ではなく候補源**である点に注意
（Wikidata 由来の誤りが実際に混ざっている）。最終的な正は
`data/journey/gazetteer.json` と `data/journey/overrides.json`。

| ファイル | 中身 | 生成 |
|---|---|---|
| `prefectures.json` | 47都道府県。団体コード2桁が正 | `scripts/ontology/build_municipalities.py` |
| `municipalities.json` | 1,979市区町村。所在地を遡るときの停止点 | 同上 |
| `places.json` | 地名 98,320件・索引語 88,801語・県境またぎ 886件 | `scripts/ontology/build_places.py`（30〜40分・県ごとキャッシュで再開可） |
| `places.json.gz` | 上の圧縮版。**Git に入っているのはこちら** | `places.json` を作り直したら `gzip -kf places.json`（`build_places.py` は作らない） |
| `prefectures.geojson` | 県境ポリゴン 1,253個。GPS から県を引く。トップの地方シルエットの元にもなる | 下記 |

`places.json`（11.7MB）は `.git/info/exclude` で外してあり、無ければ `scripts/journey/gazetteer.py` が
`places.json.gz` を読む。GitHub Actions の Journey 同期はこちらを使う。`places.json` を作り直したら
`places.json.gz` も作り直すこと（片方だけ新しいと、手元と Actions で判定が食い違う）。

## prefectures.geojson

出典: 国土数値情報「行政区域データ」N03（国土交通省）2026-01-01 版。

```bash
# 803MB。リポジトリの外に置く
mkdir -p ~/dev/data/kokudo && cd ~/dev/data/kokudo
curl -sSL -O https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2026/N03-20260101_GML.zip
unzip -o N03-20260101_GML.zip N03-20260101_prefecture.geojson

cd ~/dev/web/portfolio-astro
python3 scripts/ontology/build_boundaries.py \
  ~/dev/data/kokudo/N03-20260101_prefecture.geojson -t 0.002 -m 0.005
```

1,101万点を9万点に落としている（0.8%）。`-m 0.005` は差し渡し約600m未満の岩礁を
捨てる指定で、与論島（約20km）のような実際に投稿がある島は残る。捨てた島の上の
写真は `scripts/journey/geo.py` の最近傍（15km以内）で拾われる。

実測 943 点での比較では、より簡略な dataofjapan/land 版に対して内側判定が
920→931 に増え、最近傍での補正が 23→12 に減った。差が出た 13 点はすべて
県境上（四国カルスト・よみうりランド・十和田湖周辺）。

## 地方シルエット

トップの地方グリッドのヘッダーに透かしで入れている各地方の形は、`prefectures.geojson` から作る。

```bash
python3 scripts/journey/build_region_silhouettes.py   # → src/lib/region-silhouettes.json
```

地方ごとに県境をまとめて平面に投影し、簡略化する。透かしの大きさで点にしかならない小島は落とし、
沖縄は本島だけを九州の左下へ差し込みの要領で寄せる（そのままだと九州が小さくなる）。

