#!/usr/bin/env python3
"""テーマ軸（被写体でまとめる軸）の件数を埋め、新しい候補を提案する。

都道府県・旅・聖地巡礼に続く4つめの軸。「空」「雪」「花」のように、
土地ではなく被写体が主題の投稿をまとめる。

**テーマタグは県が散ることで見分けられる。** 旅タグや地名タグは同じタグを持つ
投稿の県が1つに揃うのに対し、テーマタグは全国に散る。旅グループ継承で使った
判定をそのまま裏返している。

ただしそれだけでは旅タグ（複数県をまたぐ旅）や地名（東京・富士山）も混ざるので、
すでに他の軸で使われているタグと、地名として引けるタグを機械的に除く。
最後に残った候補から何をテーマにするかは人が決める（themes.json を直接編集）。

この軸は場所が分からない投稿の受け皿にもなる。「空の写真」は県が特定できなくても
空のページには出せる。県軸から漏れたものをテーマ軸が拾う。
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gazetteer import Gazetteer, normalize  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"

# 候補とみなす下限。実データの分布から決めた（2投稿以上のタグ904件のうち、
# 3県以上に散るものが104件、5県以上が56件）。
MIN_PREFECTURES = 3
MIN_POSTS = 4

# 被写体ではなく行為を指す語。テーマとしては弱いので候補から外す。
NOT_A_SUBJECT = {
    "散策", "散歩", "ドライブ", "旅", "電車旅", "バス旅", "観光", "巡礼", "聖地", "聖地巡礼",
    "アニメ聖地", "アニメ聖地巡礼", "vlog", "日帰り", "一人旅", "グルメ", "ランチ",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--themes", type=pathlib.Path, default=JOURNEY / "themes.json")
    parser.add_argument("--suggest", action="store_true", help="新しいテーマの候補を出す")
    args = parser.parse_args()

    posts = json.loads((JOURNEY / "posts.json").read_text(encoding="utf-8"))["posts"]
    resolved = json.loads((JOURNEY / "resolved.json").read_text(encoding="utf-8"))["posts"]
    document = json.loads(args.themes.read_text(encoding="utf-8"))

    by_tag = collections.defaultdict(list)
    for post in posts:
        for tag in post["hashtags"]:
            by_tag[normalize(tag)].append(post)

    claimed = set()
    for theme in document["themes"]:
        members, seen = [], set()
        for tag in theme["tags"]:
            for post in by_tag.get(normalize(tag), []):
                if post["id"] not in seen:
                    seen.add(post["id"])
                    members.append(post)
        members.sort(key=lambda p: p["date"], reverse=True)
        counts = collections.Counter(
            code for p in members for code in (resolved[p["id"]]["prefCodes"] or [])
        )
        theme["postCount"] = len(members)
        theme["prefCodes"] = [code for code, _ in counts.most_common()]
        theme["postIds"] = [p["id"] for p in members]
        claimed.update(normalize(t) for t in theme["tags"])

    args.themes.write_text(
        json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"{args.themes}")
    prefectures = {
        p["code"]: p["name"]
        for p in json.loads((ROOT / "data" / "ontology" / "prefectures.json").read_text(encoding="utf-8"))
    }
    for theme in document["themes"]:
        where = "/".join(prefectures[c] for c in theme["prefCodes"][:4])
        print(f"  {theme['postCount']:3d}件 {len(theme['prefCodes']):2d}県  {theme['title']:<6} {where}")

    if not args.suggest:
        return

    # 新しい候補。すでにどこかの軸で使われているタグと地名は除く。
    gaz = Gazetteer()
    used = set(claimed)
    for name in ("trips.json", "pilgrimages.json"):
        path = JOURNEY / name
        if not path.exists():
            continue
        blob = json.loads(path.read_text(encoding="utf-8"))
        for item in blob.get("trips", []) + blob.get("works", []):
            used.add(normalize(item.get("tag", "")))
            used.update(normalize(t) for t in item.get("spots", []) + item.get("aliases", []))

    rows = []
    for tag, group in by_tag.items():
        if tag in used or tag in NOT_A_SUBJECT or len(group) < MIN_POSTS:
            continue
        if gaz.lookup(tag) or tag in gaz.pref_terms:
            continue  # 地名として引けるならテーマではない
        counts = collections.Counter(
            code for p in group for code in (resolved[p["id"]]["prefCodes"] or [])
        )
        if len(counts) >= MIN_PREFECTURES:
            rows.append((len(group), len(counts), tag))

    rows.sort(reverse=True)
    print(f"\n新しいテーマの候補 {len(rows)} 件（{MIN_POSTS}投稿以上・{MIN_PREFECTURES}県以上に散る）:")
    for count, spread, tag in rows[:40]:
        print(f"  {count:3d}件 {spread:2d}県  #{tag}")


if __name__ == "__main__":
    main()
