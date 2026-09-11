#!/usr/bin/env python3
"""エクスポートの中に紛れている自分の投稿のURLを拾って permalinks.json に入れる。

エクスポートは自分の投稿の permalink を持っていない。media id からショートコードを
計算する方法も使えない（実測で確認: ショートコードが表す pk は 3.4e18 前後、
エクスポートの fbid は 1.8e16 前後で、差も比も一致しない）。

ただし「いいねした投稿」「保存した投稿」には URL が残っていて、自分の投稿を
自分でいいねしていれば、そこから一部を回収できる。キャプションの完全一致で
突き合わせる（実測3件すべて一致）。

残りは Instagram API の permalink フィールドで埋める想定。このスクリプトは
何度流しても既存の対応を壊さない。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
INVISIBLE = re.compile(r"[⁠-⁤​-‏﻿]")
POST_URL = re.compile(r"https://www\.instagram\.com/(?:p|reel)/[^/]+/")

SOURCES = [
    "your_instagram_activity/likes/liked_posts.json",
    "your_instagram_activity/saved/saved_posts.json",
]


def demojibake(value):
    if isinstance(value, str):
        try:
            return value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    if isinstance(value, list):
        return [demojibake(v) for v in value]
    if isinstance(value, dict):
        return {demojibake(k): demojibake(v) for k, v in value.items()}
    return value


def clean(text):
    return INVISIBLE.sub("", text or "").strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=pathlib.Path, help="エクスポートの展開先")
    parser.add_argument("--handle", default="a_traveler_who_pursue_nature")
    parser.add_argument("--posts", type=pathlib.Path, default=ROOT / "data" / "journey" / "posts.json")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "data" / "journey" / "permalinks.json")
    args = parser.parse_args()

    posts = json.loads(args.posts.read_text(encoding="utf-8"))["posts"]
    by_caption = {clean(p["caption"]): p["id"] for p in posts if p["caption"]}

    existing = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    found = 0

    for name in SOURCES:
        path = args.export / name
        if not path.exists():
            continue
        for entry in demojibake(json.loads(path.read_text(encoding="utf-8"))):
            blob = json.dumps(entry, ensure_ascii=False)
            if args.handle not in blob:
                continue
            labels = {e.get("label"): e for e in entry.get("label_values", [])}
            url = (labels.get("URL") or {}).get("value", "")
            caption = clean((labels.get("キャプション") or {}).get("value", ""))
            if not POST_URL.fullmatch(url) or not caption:
                continue
            post_id = by_caption.get(caption)
            if post_id and post_id not in existing:
                existing[post_id] = url
                found += 1

    args.out.write_text(
        json.dumps(existing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    total = sum(1 for k in existing if not k.startswith("_"))
    print(f"新たに回収 {found} 件 / 合計 {total} 件 ({total / len(posts):.1%})")
    print(f"残り {len(posts) - total} 件は Instagram API などで埋める必要がある")


if __name__ == "__main__":
    main()
