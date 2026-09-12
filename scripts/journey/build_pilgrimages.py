#!/usr/bin/env python3
"""聖地巡礼のまとめを作る。作品ごとに投稿を束ね、data/journey/pilgrimages.json へ。

作品名は本人の書き方が揺れる（「俺ガイル」と「俺の青春ラブコメはまちがっている」は
同じ作品）。機械は候補を出すだけで、正式名と別名の束ね方は人が trips.json と
同じように直す前提。`--merge` で手直しを保つ。

聖地巡礼の軸は都道府県・旅の軸と排他ではない。同じ投稿が県ページにも旅ページにも
聖地巡礼ページにも出るのは仕様。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gazetteer import Gazetteer, normalize  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"

HOLY = re.compile(r"聖地")

# 聖地タグから作品名を取り出すために剥がす飾り。
DECORATION = re.compile(r"(アニメ|聖地巡礼|聖地巡り|聖地|巡礼|MAP|マップ|旅|編|ラッピングバス.*|で向かう.*)")

# 作品名として短すぎる語は拾わない。
MIN_TITLE = 3

# 作品名の候補として認める最小の投稿数。1投稿だけの作品は候補に上げず、
# unassigned に残して人が拾えるようにする（#パネル #すみだ のような
# 同時タグを作品名と取り違えないため）。
MIN_POSTS = 2

# 聖地巡礼の投稿によく付くが作品名ではない語。
NOT_A_TITLE = {
    "電車旅", "バス旅", "巡礼", "グッズ", "紅葉シーズン", "聖地巡礼",
    "アニメ", "観光", "散策", "ドライブ", "日帰り", "一人旅",
    "青春18切符", "青春18きっぷ", "きゅんパス", "フェリー", "高速バス",
}


# 作品名からURLに使うスラッグへの対応。ここに無い作品は work-N になるので、
# pilgrimages.json を直接編集して付け直す（--merge で保たれる）。
SLUGS = {
    "ゆるキャン": "yurucamp",
    "ヤマノススメ": "yama-no-susume",
    "俺ガイル": "oregairu",
    "俺の青春ラブコメはまちがっている": "oregairu",
    "沖ツラ": "okitsura",
    "ぼざろ": "bocchi-the-rock",
    "ぼっち・ざ・ろっく": "bocchi-the-rock",
    "氷菓": "hyouka",
    "リコリスリコイル": "lycoris-recoil",
    "弱虫ペダル": "yowamushi-pedal",
}


def candidate_titles(posts):
    """聖地タグを剥がした残りと、聖地投稿に頻出する非地名タグを候補にする。"""
    gaz = Gazetteer()
    titles = collections.Counter()
    for post in posts:
        for tag in post["hashtags"]:
            if HOLY.search(tag):
                stripped = DECORATION.sub("", tag).strip()
                if len(stripped) >= MIN_TITLE and stripped not in NOT_A_TITLE:
                    titles[stripped] += 1
            elif (
                not gaz.lookup(tag)
                and normalize(tag) not in gaz.pref_terms
                and len(tag) >= MIN_TITLE
                and tag not in NOT_A_TITLE
            ):
                # 地名でないタグ。作品名かもしれない
                titles[tag] += 1
    return titles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=JOURNEY / "pilgrimages.json")
    parser.add_argument("--merge", action="store_true", help="既存の手直しを保つ")
    args = parser.parse_args()

    posts = json.loads((JOURNEY / "posts.json").read_text(encoding="utf-8"))["posts"]
    resolved = json.loads((JOURNEY / "resolved.json").read_text(encoding="utf-8"))["posts"]

    holy_posts = [p for p in posts if any(HOLY.search(t) for t in p["hashtags"])]
    titles = candidate_titles(holy_posts)

    previous = {}
    if args.merge and args.out.exists():
        # 引くのは候補名（aliases）。title を正式名称に直すと機械が出す名前と
        # 一致しなくなるので、title で引くと手直しごと作り直されてしまう。
        for work in json.loads(args.out.read_text(encoding="utf-8"))["works"]:
            for key in [work["title"], *work.get("aliases", [])]:
                previous.setdefault(normalize(key), work)

    # 候補のうち十分な投稿があるものを、長い名前から順に確定させる。
    # 「ヤマノススメ聖地巡礼」より「ヤマノススメ」が残るよう剥がしてあるので、
    # ここでは投稿数の多い順に取り、既に割り当てた投稿は再利用しない。
    works, assigned = [], set()
    for title, _ in sorted(titles.items(), key=lambda kv: (-kv[1], kv[0])):
        key = normalize(title)
        group = [
            p
            for p in holy_posts
            if p["id"] not in assigned and any(key in normalize(t) for t in p["hashtags"])
        ]
        if len(group) < MIN_POSTS:
            continue
        old = previous.get(key, {})
        if old.get("hidden"):
            assigned.update(p["id"] for p in group)
            continue
        assigned.update(p["id"] for p in group)
        dates = sorted(dt.date.fromisoformat(p["date"]) for p in group)
        counts = collections.Counter(
            code for p in group for code in (resolved[p["id"]]["prefCodes"] or [])
        )
        works.append(
            {
                "slug": old.get("slug") or SLUGS.get(title, f"work-{len(works) + 1}"),
                "title": old.get("title") or title,
                "aliases": old.get("aliases") or [title],
                "postCount": len(group),
                "start": dates[0].isoformat(),
                "end": dates[-1].isoformat(),
                "prefCodes": [code for code, _ in counts.most_common()],
                "postIds": [p["id"] for p in group],
            }
        )

    works.sort(key=lambda w: -w["postCount"])
    leftovers = [
        {
            "id": p["id"],
            "date": p["date"],
            "caption": " / ".join(p["caption"].splitlines()[:1])[:60],
            "hashtags": p["hashtags"][:8],
        }
        for p in holy_posts
        if p["id"] not in assigned
    ]
    args.out.write_text(
        json.dumps({"works": works, "unassigned": leftovers}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"{args.out} に作品 {len(works)} 件（聖地タグのある投稿 {len(holy_posts)} 件）")
    pref = {p["code"]: p["name"] for p in json.loads((ROOT / "data" / "ontology" / "prefectures.json").read_text(encoding="utf-8"))}
    for w in works:
        where = "/".join(pref[c] for c in w["prefCodes"][:3])
        print(f"  {w['postCount']:3d}投稿  {w['start']}〜{w['end']}  {where:<18} {w['title']}")
    unassigned = [p for p in holy_posts if p["id"] not in assigned]
    if unassigned:
        print(f"\n  作品に束ねられなかった投稿 {len(unassigned)} 件:")
        for p in unassigned[:8]:
            print(f"    {p['date']}  {' '.join('#' + t for t in p['hashtags'][:6])}")


if __name__ == "__main__":
    main()
