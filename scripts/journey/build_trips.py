#!/usr/bin/env python3
"""旅グループを抽出して data/journey/trips.json を作る。

本人は旅ごとに「#新幹線セール2泊3日の梅雨シーズン秋田観光旅」のような
一文まるごとのタグを付けている。一方「#あしかがフラワーパーク」のような
施設名も長いタグになる。両者は **タグ自体がオントロジーの地名に完全一致
するか** で切り分けられる（地名に一致するなら場所であって旅ではない）。

出力は提案であって確定ではない。`trips.json` は人が直す前提のファイルで、
一度書いたら以後は `--merge` で既存の手直しを保ったまま更新する。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gazetteer import Gazetteer  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"

# 旅とみなす条件。数字は実データの分布から決めた（2投稿以上のタグ960件のうち、
# 期間14日以内に収まるものが571件、10文字以上は58件）。
MIN_POSTS = 3
MAX_SPAN_DAYS = 14
MIN_TAG_LENGTH = 10


def slugify(date, pref_slug, taken):
    """2025-06-akita の形。同じ月・同じ県の旅が複数あれば連番を足す。"""
    base = f"{date[:7]}-{pref_slug}"
    slug, n = base, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1
    taken.add(slug)
    return slug


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=JOURNEY / "trips.json")
    parser.add_argument(
        "--merge", action="store_true", help="既存 trips.json の手直し（title・除外）を保つ"
    )
    args = parser.parse_args()

    posts = json.loads((JOURNEY / "posts.json").read_text(encoding="utf-8"))["posts"]
    resolved = json.loads((JOURNEY / "resolved.json").read_text(encoding="utf-8"))["posts"]
    pref_slug = {
        p["code"]: p["slug"]
        for region in json.loads((JOURNEY / "prefectures.json").read_text(encoding="utf-8"))["regions"]
        for p in region["prefectures"]
    }
    gaz = Gazetteer()

    by_tag = collections.defaultdict(list)
    for post in posts:
        for tag in post["hashtags"]:
            by_tag[tag].append(post)

    candidates = []
    for tag, group in by_tag.items():
        if len(group) < MIN_POSTS or len(tag) < MIN_TAG_LENGTH:
            continue
        dates = sorted(dt.date.fromisoformat(p["date"]) for p in group)
        if (dates[-1] - dates[0]).days > MAX_SPAN_DAYS:
            continue
        # タグそのものが地名なら、それは旅ではなく場所。
        if gaz.lookup(tag):
            continue
        counts = collections.Counter(
            code for p in group for code in (resolved[p["id"]]["prefCodes"] or [])
        )
        if not counts:
            continue
        candidates.append((dates[0], dates[-1], tag, group, counts))

    # 同じ日程に重なる候補は同じ旅を指している。「ユニバーサルスタジオジャパン」
    # 「ホテルユニバーサルポート」「スーパーニンテンドーワールド」は 2024-02-14〜16 の
    # 一つの旅であって三つではない。投稿数の最も多いタグを旅の名前とし、
    # 残りはその旅の中の立ち寄り先として spots に畳む。
    candidates.sort(key=lambda c: (-len(c[3]), c[0]))
    clusters = []
    for start, end, tag, group, counts in candidates:
        for cluster in clusters:
            if start <= cluster["end"] and cluster["start"] <= end:
                cluster["spots"].append(tag)
                cluster["group"] = {p["id"]: p for p in [*cluster["group"].values(), *group]}
                cluster["start"] = min(cluster["start"], start)
                cluster["end"] = max(cluster["end"], end)
                break
        else:
            clusters.append(
                {
                    "start": start,
                    "end": end,
                    "tag": tag,
                    "group": {p["id"]: p for p in group},
                    "spots": [],
                }
            )

    candidates = [
        (
            c["start"],
            c["end"],
            c["tag"],
            list(c["group"].values()),
            collections.Counter(
                code for p in c["group"].values() for code in (resolved[p["id"]]["prefCodes"] or [])
            ),
            c["spots"],
        )
        for c in clusters
    ]
    candidates.sort(key=lambda c: c[0], reverse=True)

    previous = {}
    if args.merge and args.out.exists():
        previous = {t["tag"]: t for t in json.loads(args.out.read_text(encoding="utf-8"))["trips"]}

    taken, trips = set(), []
    for start, end, tag, group, counts, spots in candidates:
        old = previous.get(tag, {})
        if old.get("hidden"):
            continue
        # 件数が多い順の県。1件しか無い県は立ち寄りなので主役から外す。
        main = [code for code, n in counts.most_common() if n > 1] or [counts.most_common(1)[0][0]]
        trips.append(
            {
                "slug": old.get("slug") or slugify(start.isoformat(), pref_slug[main[0]], taken),
                "tag": tag,
                "title": old.get("title") or tag,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "postCount": len(group),
                "prefCodes": main,
                "allPrefCodes": [code for code, _ in counts.most_common()],
                "spots": old.get("spots") or spots,
            }
        )

    args.out.write_text(
        json.dumps({"trips": trips}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    covered = len({p["id"] for c in candidates for p in c[3]})
    print(f"{args.out} に旅 {len(trips)} 件（投稿 {covered} 件をカバー）")
    for t in trips:
        print(f"  {t['slug']:<22} {t['postCount']:3d}投稿  {t['start']}〜{t['end']}  {t['title'][:40]}")


if __name__ == "__main__":
    main()
