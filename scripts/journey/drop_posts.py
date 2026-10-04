#!/usr/bin/env python3
"""保留する投稿を取り込みデータとサムネイルから取り除く。派生データは journey:build で作り直す。"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT, help="取り込みを済ませた作業ツリー")
    parser.add_argument("--ids", required=True, help="取り除く投稿ID（カンマ区切り）")
    args = parser.parse_args()

    ids = {post_id.strip() for post_id in args.ids.split(",")}
    if not all(post_id.isascii() and post_id.isdecimal() for post_id in ids):
        parser.error("--ids は数字の投稿IDをカンマで区切って指定する")
    posts_path = args.root / "data/journey/posts.json"
    permalinks_path = args.root / "data/journey/permalinks.json"
    document = json.loads(posts_path.read_text(encoding="utf-8"))
    permalinks = json.loads(permalinks_path.read_text(encoding="utf-8"))
    before = len(document["posts"])
    document["posts"] = [p for p in document["posts"] if p["id"] not in ids]
    for post_id in ids:
        permalinks.pop(post_id, None)

    # 取り込みと同じ書式で、残す投稿の順序や同期日時は変えない
    posts_path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    permalinks_path.write_text(json.dumps(permalinks, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for post_id in ids:
        (args.root / "public/journey/thumbs" / f"{post_id}.webp").unlink(missing_ok=True)
    removed = before - len(document["posts"])
    if removed != len(ids):
        print(f"指定 {len(ids)} 件のうち {len(ids) - removed} 件は posts.json に無かった", file=sys.stderr)
    print(f"削除 {removed} 件 / 残り {len(document['posts'])} 件")


if __name__ == "__main__":
    main()
