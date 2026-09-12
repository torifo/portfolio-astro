#!/usr/bin/env python3
"""Instagram API から新着投稿だけを取り込む。エクスポートの zip を取り直さずに追いつく経路。

エクスポート（parse_export.py）とは役割が違う。

  parse_export.py  zip 全体から posts.json を作り直す。EXIF の GPS が取れる。
  sync_instagram.py  API から新着だけを足す。GPS は取れない（API は EXIF を返さない）。

GPS が無くても実用になる。実測では直近300件のうち、地名がタグにもキャプションにも
無くて GPS だけが手がかりだった投稿は 7 件（2%）しかない。昔の投稿では 28% あったが、
地名タグを付ける習慣がついてからは県の判定はタグでほぼ足りている。
残る数件は resolve.py が「未解決」に出すので、あとから overrides.json で埋めればよい。

**冪等**。同じ投稿を二度足さない。posts.json に無い ID だけを API から拾う。
古いエクスポートで parse_export.py を回して API 分が消えても、これを流せば戻る。

出力:
  data/journey/posts.json        新着を追加（撮影日の新しい順は保つ）
  data/journey/permalinks.json   新着の個別リンク
  public/journey/thumbs/<id>.webp  480px webp（API の画像を落として変換）

このあとに resolve.py → build_trips/build_pilgrimages/build_themes を回す。
`npm run journey:sync` がその並びをまとめてある。

トークンは fetch_permalinks.py と同じ場所から読む（環境変数か ~/dev/.env.dev）。
ビルドからは切り離してある。ビルド時に API を呼ぶとトークンが切れた日にサイトが落ちる。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_thumbs import to_webp  # noqa: E402
from fetch_permalinks import ENV_FILE, read_token  # noqa: E402
from parse_export import HASHTAG, clean_caption, resolve_date  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"
THUMBS = ROOT / "public" / "journey" / "thumbs"
JST = dt.timezone(dt.timedelta(hours=9))
API = "https://graph.instagram.com/v21.0/me/media"
FIELDS = (
    "id,caption,timestamp,media_type,media_url,thumbnail_url,permalink,"
    "children{media_type,media_url,thumbnail_url}"
)


def fetch_pages(token, known, limit=100):
    """新しい順に取り、既知のものしか無いページに当たったら止める。

    API は新しい順に返す。新着は先頭に固まっているので、1ページ丸ごと既知なら
    その先も既知しかない。全件取ると11ページ叩くことになるので既定で打ち切る。
    """
    url = f"{API}?{urllib.parse.urlencode({'fields': FIELDS, 'limit': limit, 'access_token': token})}"
    items, pages = [], 0
    while url:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.loads(response.read())
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            sys.exit(
                f"API が {error.code} を返した: {body}\n"
                "トークンが失効している可能性がある（長期トークンの寿命は60日）。\n"
                f"{ENV_FILE} の INSTAGRAM_ACCESS_TOKEN を貼り直す。"
            )
        page = payload.get("data", [])
        pages += 1
        items.extend(page)
        fresh = [item for item in page if item.get("id") not in known]
        print(f"  {pages}ページ目 {len(page)}件（うち新着 {len(fresh)}件）", flush=True)
        if page and not fresh:
            break
        url = payload.get("paging", {}).get("next")
    return items


def cover_url(item):
    """表紙の画像URL。カルーセルは1枚目、動画はサムネ（どちらも JPEG が返る）。"""
    kind = item.get("media_type")
    if kind == "CAROUSEL_ALBUM":
        children = (item.get("children") or {}).get("data") or []
        if not children:
            return None
        item = children[0]
        kind = item.get("media_type")
    if kind == "VIDEO":
        return item.get("thumbnail_url") or item.get("media_url")
    return item.get("media_url")


def build_record(item):
    """parse_export.build_record と同じ形。日付の解釈も同じ関数を使う。"""
    uploaded = dt.datetime.strptime(item["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(JST)
    caption = clean_caption(item.get("caption"))
    date, precision, source = resolve_date(caption, uploaded)
    return {
        "id": item["id"],
        "kind": "reel" if item.get("media_type") == "VIDEO" else "post",
        "date": date,
        "date_precision": precision,
        "date_source": source,
        "uploaded_at": uploaded.isoformat(),
        "caption": caption,
        "hashtags": HASHTAG.findall(caption),
        # エクスポート内のパス。API 由来にはそれが無いので空にしておく。
        # サムネはこのスクリプトが直接落とすので build_thumbs.py は素通りしてよい。
        "cover": None,
        "media": [],
        # GPS が無いことの目印。あとでエクスポートを取り直せば上書きされる。
        "origin": "api",
    }


def download(url, timeout=60):
    request = urllib.request.Request(url, headers={"User-Agent": "portfolio-astro/journey-sync"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts", type=pathlib.Path, default=JOURNEY / "posts.json")
    parser.add_argument("--permalinks", type=pathlib.Path, default=JOURNEY / "permalinks.json")
    parser.add_argument("--thumbs", type=pathlib.Path, default=THUMBS)
    parser.add_argument("--size", type=int, default=480)
    parser.add_argument("--quality", type=int, default=70)
    parser.add_argument("--all", action="store_true", help="既知に当たっても最後まで取る")
    parser.add_argument("--dry-run", action="store_true", help="書き込まずに何が増えるかだけ出す")
    args = parser.parse_args()

    token, source = read_token()
    if not token:
        sys.exit(
            "アクセストークンが見つからない。次のどちらかに置く:\n"
            f"  1. {ENV_FILE} の INSTAGRAM_ACCESS_TOKEN= に貼る\n"
            "  2. export INSTAGRAM_ACCESS_TOKEN='...'"
        )
    print(f"トークンの読み込み元: {source}")

    document = json.loads(args.posts.read_text(encoding="utf-8"))
    posts = document["posts"]
    known = {p["id"] for p in posts}
    print(f"手元 {len(posts)} 件。API を見る。")

    items = fetch_pages(token, set() if args.all else known)
    fresh = [item for item in items if item.get("id") not in known]
    if not fresh:
        print("\n新着なし。何も変えていない。")
        return

    fresh.sort(key=lambda item: item["timestamp"])
    print(f"\n新着 {len(fresh)} 件:")
    records, permalinks, thumb_jobs = [], {}, []
    for item in fresh:
        record = build_record(item)
        records.append(record)
        if item.get("permalink"):
            permalinks[record["id"]] = item["permalink"]
        url = cover_url(item)
        if url:
            thumb_jobs.append((record["id"], url))
        tags = " ".join(f"#{t}" for t in record["hashtags"][:6]) or "（タグ無し）"
        print(f"  {record['date']} {record['kind']:<4} {record['id']}  {tags}")

    if args.dry_run:
        print("\n--dry-run なので書き込まない。")
        return

    args.thumbs.mkdir(parents=True, exist_ok=True)
    made = failed = 0
    for post_id, url in thumb_jobs:
        destination = args.thumbs / f"{post_id}.webp"
        if destination.exists():
            continue
        try:
            data = download(url)
        except Exception as error:  # noqa: BLE001 - 失効したURLも含めてまとめて報告する
            print(f"  サムネ取得に失敗 {post_id}: {error}", file=sys.stderr)
            failed += 1
            continue
        ok, error = to_webp(data, destination, args.size, ".jpg", args.quality)
        if ok:
            made += 1
        else:
            failed += 1
            print(f"  サムネ変換に失敗 {post_id}: {error}", file=sys.stderr)

    posts.extend(records)
    posts.sort(key=lambda r: (r["date"], r["uploaded_at"]), reverse=True)
    document["posts"] = posts
    document["synced_at"] = dt.datetime.now(JST).isoformat(timespec="seconds")
    args.posts.write_text(
        json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    existing = json.loads(args.permalinks.read_text(encoding="utf-8")) if args.permalinks.exists() else {}
    existing.update(permalinks)
    args.permalinks.write_text(
        json.dumps(existing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    print(f"\n追加 {len(records)} 件 / サムネ {made} 枚（失敗 {failed}）/ 合計 {len(posts)} 件")
    print("次: python3 scripts/journey/resolve.py --report  で県の判定を確認する")


if __name__ == "__main__":
    main()
