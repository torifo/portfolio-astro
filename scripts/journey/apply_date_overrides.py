#!/usr/bin/env python3
"""date_overrides.json の指定で posts.json の日付を差し替える。

キャプションに日付が無い投稿はアップロード日時で埋まる（date_source が upload）。
旅の写真を後日あげるとその日付が実際の撮影日とずれ、旅の期間が伸びる。

sync は新着しか読まないので、Instagram 側のキャプションを直しても既にある投稿には
届かない。人が直した日付をここで上書きする。journey:build の先頭で流す。

値の書き方と精度（date_precision）:

  "2023-05-03"  日まで（day）
  "2023-05"     月まで（month）。日付は月初に寄せる
  "2022"        年まで（year）。日付は1月1日に寄せる。サイトには「2022年」と出る
  "unknown"     撮影日が分からない（unknown）。日付は投稿日のまま並び順にだけ使い、
                サイトには「日付不明」と出す。県ページの年の範囲や旅の期間には数えない
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"

UNKNOWN = "unknown"


def parse(want, post):
    """指定の値から (日付, 精度)。書き間違いはここで落とす。"""
    try:
        if want == UNKNOWN:
            return post["uploaded_at"][:10], "unknown"
        if re.fullmatch(r"\d{4}", want):
            return dt.date(int(want), 1, 1).isoformat(), "year"
        if re.fullmatch(r"\d{4}-\d{2}", want):
            return dt.date.fromisoformat(f"{want}-01").isoformat(), "month"
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", want):
            return dt.date.fromisoformat(want).isoformat(), "day"
    except (TypeError, ValueError):
        pass  # 文字列でない値（引用符の付け忘れ）・存在しない日付（2023-02-30）
    raise SystemExit(f"date_overrides.json の値が読めない: {post['id']}: {want!r}")


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
        date, precision = parse(want, post)
        # 日付が同じでも精度だけ変わることがある（"unknown" は投稿日のまま）
        if (post["date"], post["date_precision"], post["date_source"]) != (date, precision, "manual"):
            changed.append((post["id"], post["date"], want))
            post["date"] = date
            post["date_precision"] = precision
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
