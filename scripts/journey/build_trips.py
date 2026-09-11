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
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gazetteer import Gazetteer, normalize  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"

# 旅とみなす条件。
#
# **期間が効く。** 汎用タグ（散策・自然・空）は年をまたいで散るのに対し、旅タグは
# 数日から数週間に収まる。以前はタグの文字数でも絞っていたが、それは当て推量で、
# 「#東北きゅんパス旅」(8文字・49投稿・2日) のような明らかな旅を落としていた。
# 文字数の条件は外し、期間で切る。四国旅のような3週間の旅も拾えるよう30日まで許す。
MIN_POSTS = 3
MAX_SPAN_DAYS = 30

# **旅タグは、それが出た日の投稿をほぼ全部覆う。** 本人が旅ごとに付ける一文まるごとの
# タグは、その日に上げた投稿すべてに付く。一方「#あじさい」「#彫刻」のような被写体の
# タグは、同じ日の他の投稿には付かない。
#
# 期間全体での被覆率ではなく日ごとに見るのが要点。長い旅の期間には別の旅が挟まる
# ことがあり（四国旅の21日間には上高地とディズニーが混ざっていた）、期間で測ると
# 55% まで落ちて弾かれてしまう。日ごとなら 98% になる。
#
# 実データでは 四国旅98% / 東北きゅんパス旅100% / あじさい巡り96% に対し、
# テーマパーク52% / あじさい37% / 彫刻24% / 探検9% と、はっきり分かれた。
MIN_DAY_COVERAGE = 0.8


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
    posts_per_day = collections.Counter(p["date"] for p in posts)
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
        if len(group) < MIN_POSTS:
            continue
        dates = sorted(dt.date.fromisoformat(p["date"]) for p in group)
        if (dates[-1] - dates[0]).days > MAX_SPAN_DAYS:
            continue
        # タグそのものが地名・県名なら、それは旅ではなく場所。
        if gaz.lookup(tag) or normalize(tag) in gaz.pref_terms:
            continue
        # このタグが出た日ごとに、その日の投稿をどれだけ覆っているか。旅の名前なら高い。
        tagged_per_day = collections.Counter(p["date"] for p in group)
        coverage = statistics.mean(
            count / posts_per_day[day] for day, count in tagged_per_day.items()
        )
        if coverage < MIN_DAY_COVERAGE:
            continue
        counts = collections.Counter(
            code for p in group for code in (resolved[p["id"]]["prefCodes"] or [])
        )
        if not counts:
            continue
        candidates.append((dates[0], dates[-1], tag, group, counts))

    # 同じ日程の候補は同じ旅を指している。「ユニバーサルスタジオジャパン」
    # 「ホテルユニバーサルポート」「スーパーニンテンドーワールド」は 2024-02-14〜16 の
    # 一つの旅であって三つではない。投稿数の最も多いタグを旅の名前とし、
    # 残りはその旅の中の立ち寄り先として spots に畳む。
    #
    # **併合は「内側に収まる」ときだけ。** 期間が重なるだけで併合し、さらに
    # 併合のたびに期間を広げると、別々の旅が数珠つなぎになる（与論島の旅が
    # 1か月前の海ほたるドライブまで飲み込んだ）。旅の期間は主役のタグが決め、
    # 広げない。
    candidates.sort(key=lambda c: (-len(c[3]), c[0]))
    clusters = []
    for start, end, tag, group, counts in candidates:
        for cluster in clusters:
            if cluster["start"] <= start and end <= cluster["end"]:
                cluster["spots"].append(tag)
                cluster["group"] = {p["id"]: p for p in [*cluster["group"].values(), *group]}
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

    # 引き継いだ slug も先に押さえておかないと、新しい旅と衝突する。
    taken = {t["slug"] for t in previous.values() if t.get("slug")}
    trips = []
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
