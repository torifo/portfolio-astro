#!/usr/bin/env python3
"""聖地巡礼のまとめを作る。作品ごとに投稿を束ね、data/journey/pilgrimages.json へ。

作品の辞書は pilgrimages.json の works（title・aliases・slug・hidden）で、人が育てる。
機械は投稿を辞書の作品に振り分けるだけで、作品名を推し量らない（件数で作品を見分けると、
1件だけの作品が落ち、旅の名前や「#パネル」のような同時タグが作品になってしまった）。

  聖地巡礼に数える投稿  「聖地」を含むタグが投稿そのものに付いているもの。旅の名前のタグ
                        （「ゆるキャン聖地巡礼旅浜松編」のような…旅・…編）だけでは数えない
  巡礼の旅              旅の名前に「巡礼」がある旅（「…WILLERの巡礼旅」）。旅の中に上の投稿が
                        あればそれだけを数え（浜松編のさわやか・浜松城は外す）、1件も無ければ
                        旅の投稿をすべて数える
  作品への振り分け      投稿のタグに作品名か別名が入っていれば、その作品に入れる。2つあれば両方
  作品名なし            聖地巡礼に数えるのにどの作品にも入らない投稿は「作品名なし」にまとめる
                        （巡礼の旅も、作品名のタグを付けるまではここに入る）

新しい作品は works に title・aliases・slug を足す。聖地巡礼の軸は都道府県・旅の軸と排他ではなく、
同じ投稿が県ページにも旅ページにも聖地巡礼ページにも出るのは仕様。テーマの軸はこの絞り込みを持たない。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_trips import NAMED_TRIP_MIN_LENGTH, NAMED_TRIP_SUFFIXES  # noqa: E402
from gazetteer import normalize  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"

# 作品名の無い聖地巡礼をまとめる枠。works の中で untitled: true の1件
UNTITLED = {"slug": "untitled", "title": "作品名なし", "aliases": [], "untitled": True}

# 旅の名前にこの語があれば巡礼の旅（「…WILLERの巡礼旅」）
PILGRIMAGE_TRIP_WORD = "巡礼"


def is_trip_tag(tag, trip_tags):
    """旅の名前のタグ。登録済みの旅か、build_trips.py と同じ「…旅」「…編」で終わる長いタグ。"""
    return tag in trip_tags or (tag.endswith(NAMED_TRIP_SUFFIXES) and len(tag) >= NAMED_TRIP_MIN_LENGTH)


def is_holy(post, trip_tags):
    return any("聖地" in tag and not is_trip_tag(tag, trip_tags) for tag in post["hashtags"])


def trip_members(trip, posts):
    """旅のページに出る投稿（journey.ts の postsForTrip と同じく、旅のタグか立ち寄り先のタグ）。"""
    tags = {trip["tag"], *trip.get("spots", [])}
    return [p for p in posts if tags & set(p["hashtags"])]


def pilgrimage_trip_posts(trips, posts, trip_tags):
    """巡礼の旅のうち、「聖地」タグの投稿が1件も無い旅の投稿。旅ごと聖地巡礼に数える。"""
    found = []
    for trip in trips:
        if trip.get("hidden") or PILGRIMAGE_TRIP_WORD not in trip["tag"]:
            continue
        members = trip_members(trip, posts)
        if not any(is_holy(p, trip_tags) for p in members):
            found.extend(members)
    return found


def summarize(record, group, resolved):
    """作品の postIds から件数・期間・県を埋める。"""
    # 期間は撮影日の分かる投稿から（年まで・不明の投稿は日付が並び順のためだけにある）。全部そうなら全件から
    dated = [p for p in group if p["date_precision"] not in ("year", "unknown")] or group
    dates = sorted(dt.date.fromisoformat(p["date"]) for p in dated)
    counts = collections.Counter(code for p in group for code in (resolved[p["id"]]["prefCodes"] or []))
    return {
        **record,
        "postCount": len(group),
        "start": dates[0].isoformat() if dates else None,
        "end": dates[-1].isoformat() if dates else None,
        "prefCodes": [code for code, _ in counts.most_common()],
        "postIds": [p["id"] for p in group],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=pathlib.Path, default=JOURNEY / "pilgrimages.json")
    parser.add_argument("--merge", action="store_true", help="互換のため残す（辞書は常に --out の works から読む）")
    args = parser.parse_args()

    posts = json.loads((JOURNEY / "posts.json").read_text(encoding="utf-8"))["posts"]
    resolved = json.loads((JOURNEY / "resolved.json").read_text(encoding="utf-8"))["posts"]
    posts = [p for p in posts if not resolved.get(p["id"], {}).get("hidden")]  # 日付の後ろに「趣味」は載せない
    trips = json.loads((JOURNEY / "trips.json").read_text(encoding="utf-8"))["trips"]
    trip_tags = {t["tag"] for t in trips}
    dictionary = [
        w for w in json.loads(args.out.read_text(encoding="utf-8"))["works"] if not w.get("untitled")
    ]

    holy_posts = [p for p in posts if is_holy(p, trip_tags)]
    seen = {p["id"] for p in holy_posts}
    for post in pilgrimage_trip_posts(trips, posts, trip_tags):
        if post["id"] not in seen:
            seen.add(post["id"])
            holy_posts.append(post)
    works, rest, assigned = [], [], set()
    for entry in dictionary:
        keys = [normalize(k) for k in [entry["title"], *entry.get("aliases", [])]]
        group = [p for p in holy_posts if any(k in normalize(t) for k in keys for t in p["hashtags"])]
        assigned.update(p["id"] for p in group)
        record = {k: entry[k] for k in ("slug", "title", "aliases") if k in entry}
        if entry.get("hidden"):
            # 除外の印は書き戻す。サイト側（journey.ts）が hidden を弾く
            rest.append({**summarize(record, group, resolved), "hidden": True})
        elif group:
            works.append(summarize(record, group, resolved))
        else:
            rest.append(summarize(record, group, resolved))  # 投稿がまだ無い作品も辞書には残す（サイトは postCount 0 を出さない）

    works.sort(key=lambda w: -w["postCount"])
    untitled = [p for p in holy_posts if p["id"] not in assigned]
    if untitled:
        works.append(summarize(UNTITLED, untitled, resolved))
    args.out.write_text(
        json.dumps({"works": works + rest}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    print(f"{args.out} に作品 {sum(1 for w in works if not w.get('untitled'))} 件（聖地巡礼に数える投稿 {len(holy_posts)} 件）")
    pref = {p["code"]: p["name"] for p in json.loads((ROOT / "data" / "ontology" / "prefectures.json").read_text(encoding="utf-8"))}
    for w in works:
        where = "/".join(pref[c] for c in w["prefCodes"][:3])
        print(f"  {w['postCount']:3d}投稿  {w['start']}〜{w['end']}  {where:<18} {w['title']}")
    for w in rest:
        print(f"  （{'除外' if w.get('hidden') else '投稿なし'}）{w['postCount']:3d}投稿  {w['title']}")
    if untitled:
        print(f"\n  作品名なし {len(untitled)} 件（作品なら works に title・aliases を足す）:")
        for p in untitled[:8]:
            print(f"    {p['date']}  {' '.join('#' + t for t in p['hashtags'][:8])}")


if __name__ == "__main__":
    main()
