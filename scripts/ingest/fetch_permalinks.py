#!/usr/bin/env python3
"""Instagram API から投稿の permalink を取得して permalinks.json を埋める。

データエクスポートは自分の投稿の permalink を持たず、media id からショートコードを
計算することもできない（実測で確認済み。data/ontology/README.md 参照）。
個々の投稿へリンクするには API から取るしかない。

トークンは次の順で探す。コマンドライン引数では受け取らない（履歴に残るため）。

  1. 環境変数 INSTAGRAM_ACCESS_TOKEN
  2. ~/dev/.env.dev の INSTAGRAM_ACCESS_TOKEN=...

~/dev は git 管理下ではないので、2 に置いた値が履歴に載ることはない。
リポジトリ内の .env は microCMS 用で GitHub Actions から配られるため、
そこに個人のトークンを混ぜない。

このスクリプトはビルドから切り離されている。ビルド時に API を呼ぶと
トークンが切れた日にサイトが落ちるので、呼ぶのは手元だけ。
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
# ~/dev/.env.dev。リポジトリの2つ上（web/ の親）に置いてある。
ENV_FILE = ROOT.parents[1] / ".env.dev"
API = "https://graph.instagram.com/v21.0/me/media"
FIELDS = "id,permalink,caption,timestamp,media_type"
INVISIBLE = re.compile(r"[⁠-⁤​-‏﻿]")


def clean(text):
    return INVISIBLE.sub("", text or "").strip()


def read_token():
    """環境変数、無ければ ~/dev/.env.dev から読む。"""
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if token:
        return token.strip(), "環境変数"
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("INSTAGRAM_ACCESS_TOKEN="):
                value = line.split("=", 1)[1].strip().strip("'\"")
                if value:
                    return value, str(ENV_FILE)
    return None, None


def fetch_all(token, limit=100):
    """paging.next をたどって全件取る。"""
    url = f"{API}?{urllib.parse.urlencode({'fields': FIELDS, 'limit': limit, 'access_token': token})}"
    items = []
    while url:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read())
        items.extend(payload.get("data", []))
        url = payload.get("paging", {}).get("next")
        print(f"  取得 {len(items)} 件", flush=True)
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts", type=pathlib.Path, default=ROOT / "data" / "journey" / "posts.json")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "data" / "journey" / "permalinks.json")
    parser.add_argument("--dump", type=pathlib.Path, help="APIの生の応答を保存する（デバッグ用）")
    args = parser.parse_args()

    token, source = read_token()
    if not token:
        sys.exit(
            "アクセストークンが見つからない。次のどちらかに置く:\n"
            f"  1. {ENV_FILE} の INSTAGRAM_ACCESS_TOKEN= に貼る\n"
            "  2. export INSTAGRAM_ACCESS_TOKEN='...'"
        )
    print(f"トークンの読み込み元: {source}")

    posts = json.loads(args.posts.read_text(encoding="utf-8"))["posts"]
    by_id = {p["id"]: p for p in posts}
    by_caption = {clean(p["caption"]): p["id"] for p in posts if p["caption"]}

    media = fetch_all(token)
    if args.dump:
        args.dump.write_text(json.dumps(media, ensure_ascii=False, indent=1), encoding="utf-8")

    existing = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    by_id_hits = by_caption_hits = missed = 0

    for item in media:
        permalink = item.get("permalink")
        if not permalink:
            continue
        # エクスポートの fbid と API の id が同じならそのまま結べる。
        # 違っていてもキャプションの完全一致で結べる（実測で有効）。
        post_id = None
        if item.get("id") in by_id:
            post_id, by_id_hits = item["id"], by_id_hits + 1
        else:
            post_id = by_caption.get(clean(item.get("caption")))
            if post_id:
                by_caption_hits += 1
        if post_id:
            existing[post_id] = permalink
        else:
            missed += 1

    args.out.write_text(json.dumps(existing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(1 for key in existing if not key.startswith("_"))
    print(f"\nAPI から {len(media)} 件")
    print(f"  id で一致        : {by_id_hits}")
    print(f"  キャプションで一致: {by_caption_hits}")
    print(f"  結べなかった      : {missed}")
    print(f"{args.out}: 合計 {total} / {len(posts)} 件 ({total / len(posts):.1%})")


if __name__ == "__main__":
    main()
