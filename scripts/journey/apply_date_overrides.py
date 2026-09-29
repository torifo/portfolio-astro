#!/usr/bin/env python3
"""date_overrides.json の指定で posts.json の日付を差し替える。

キャプションに日付が無い投稿はアップロード日時で埋まる（date_source が upload）。
旅の写真を後日あげるとその日付が実際の撮影日とずれ、旅の期間が伸びる。

sync は新着しか読まないので、Instagram 側のキャプションを直しても既にある投稿には
届かない。人が直した日付をここで上書きする。journey:build の先頭で流す。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts", type=pathlib.Path, default=JOURNEY / "posts.json")
    parser.add_argument("--overrides", type=pathlib.Path, default=JOURNEY / "date_overrides.json")
    args = parser.parse_args()

    if not args.overrides.exists():
        print("date_overrides.json が無いので何もしない")
        return

    # 先頭が _ のキーは覚書
    overrides = {
        k: v for k, v in json.loads(args.overrides.read_text(encoding="utf-8")).items()
        if not k.startswith("_")
    }
    data = json.loads(args.posts.read_text(encoding="utf-8"))

    changed, missing = [], []
    for post in data["posts"]:
        want = overrides.pop(post["id"], None)
        if want is None:
            continue
        dt.date.fromisoformat(want)  # 書き間違いはここで落とす
        if post["date"] != want:
            changed.append((post["id"], post["date"], want))
            post["date"] = want
        post["date_precision"] = "day"
        post["date_source"] = "manual"
    missing = list(overrides)

    if changed:
        data["posts"].sort(key=lambda r: (r["date"], r["uploaded_at"]), reverse=True)
        args.posts.write_text(
            json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )

    print(f"日付の上書き {len(changed)} 件")
    for post_id, before, after in changed:
        print(f"  {post_id}  {before} -> {after}")
    for post_id in missing:
        print(f"  該当する投稿が無い: {post_id}")


if __name__ == "__main__":
    main()
