#!/usr/bin/env python3
"""取り込み済みの投稿のキャプションを API から読み直す。

sync_instagram.py は新着しか足さないので、Instagram 側でキャプションやタグを直しても
取り込み済みの投稿には届かない（旅の名前のタグに「巡礼」を足した、など）。
これは全ページを読み、キャプションが変わった投稿の caption・hashtags を書き換える。

  撮影日      本文の先頭の日付から読み直す。人が指定した撮影日（date_source が manual）は
              そのまま（date_overrides.json が journey:build の先頭でまた当てる）
  新着        足さない。新着は同期の PR で取り込む
  そのほか    サムネ・個別リンク・県の指定（overrides.json）には触れない

旅の名前のタグを付け直すと旅の URL（slug）が変わる。trips.json の該当する旅の tag を
新しいタグに書き換えてから journey:build すると、今の slug を引き継ぐ。

`npm run journey:refresh` で、このあと journey:build まで流す。
トークンは sync_instagram.py と同じ場所から読む（環境変数か ~/dev/.env.dev）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fetch_permalinks import ENV_FILE, read_token  # noqa: E402
from parse_export import HASHTAG, clean_caption, resolve_date  # noqa: E402
from sync_instagram import fetch_pages  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--posts", type=pathlib.Path, default=JOURNEY / "posts.json")
    parser.add_argument("--dry-run", action="store_true", help="書き込まずに何が変わるかだけ出す")
    args = parser.parse_args()

    token, source = read_token()
    if not token:
        sys.exit(f"アクセストークンが見つからない。{ENV_FILE} の INSTAGRAM_ACCESS_TOKEN= か環境変数に置く")
    print(f"トークンの読み込み元: {source}")

    document = json.loads(args.posts.read_text(encoding="utf-8"))
    posts = {p["id"]: p for p in document["posts"]}
    print(f"手元 {len(posts)} 件。API を全ページ読む。")
    items = fetch_pages(token, set())

    changed, skipped = [], []
    for item in items:
        post = posts.get(item.get("id"))
        caption = clean_caption(item.get("caption"))
        if not post or caption == post["caption"]:
            continue
        if not caption:
            skipped.append(post)  # API が本文を返さなかっただけかもしれないので、空では上書きしない
            continue
        before = post["hashtags"]
        post["caption"] = caption
        post["hashtags"] = HASHTAG.findall(caption)
        if post["date_source"] != "manual":
            uploaded = dt.datetime.fromisoformat(post["uploaded_at"])
            post["date"], post["date_precision"], post["date_source"] = resolve_date(caption, uploaded)
        changed.append((post, before))

    print(f"\nキャプションが変わった投稿 {len(changed)} 件:")
    for post, before in changed:
        removed = " ".join(f"-#{t}" for t in before if t not in post["hashtags"])
        added = " ".join(f"+#{t}" for t in post["hashtags"] if t not in before)
        print(f"  {post['date']} {post['id']}  {removed} {added}".rstrip())
    for post in skipped:
        print(f"  本文が空で返ったので飛ばした: {post['date']} {post['id']}（消したなら手で直す）")
    if not changed or args.dry_run:
        print("\n書き込まない。" if changed else "\n何も変えていない。")
        return

    document["posts"] = sorted(posts.values(), key=lambda r: (r["date"], r["uploaded_at"]), reverse=True)
    args.posts.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n次: npm run journey:build（journey:refresh なら続けて流れる）")


if __name__ == "__main__":
    main()
