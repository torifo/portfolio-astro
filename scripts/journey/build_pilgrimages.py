#!/usr/bin/env python3
"""聖地巡礼のまとめを作る。作品ごとに投稿を束ね、data/journey/pilgrimages.json へ。

作品の辞書は pilgrimages.json の works（title・aliases・slug・spots・extraPostIds・hidden）で、人が育てる。
機械は投稿を辞書の作品に振り分けるだけで、作品名を推し量らない（件数で作品を見分けると、
1件だけの作品が落ち、旅の名前や「#パネル」のような同時タグが作品になってしまった）。

  聖地巡礼に数える投稿  「聖地」を含むタグが投稿そのものに付いているもの。旅の名前のタグ
                        （「ゆるキャン聖地巡礼旅浜松編」のような…旅・…編）だけでは数えない
  作品への振り分け      投稿のタグに作品名か別名が入っていれば、その作品に入れる。2つあれば両方
  聖地の場所（spots）   作品の聖地として人が登録した場所のタグ。そのタグの投稿は聖地巡礼タグが無くても
                        その作品に入れる（弱虫ペダルの伊勢志摩スカイライン）
  extraPostIds          人が個別に入れる投稿。本文に「〇〇聖地巡礼」と書いてタグを付けていない投稿など
  作品を推し量る        聖地巡礼に数えるのにタグで作品に入らない投稿（タグは5つまでなので作品名を付けられないことがある）は、
                        同じ日のほかの投稿が入った作品を見る。1つならその作品に入れる。同じ日に作品が無ければ同じ旅の投稿に
                        広げ、1つならその作品に入れる。2つ以上なら決めずに「作品名なし」に残し、候補を candidates に書く
                        （同期 PR は自動マージしない）。推し量った投稿は作品の inferred に「同じ日」「同じ旅」と書く
  作品名なし            聖地巡礼に数えるのにどの作品にも入らない投稿は「作品名なし」にまとめる

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


def is_trip_tag(tag, trip_tags):
    """旅の名前のタグ。登録済みの旅か、build_trips.py と同じ「…旅」「…編」で終わる長いタグ。"""
    return tag in trip_tags or (tag.endswith(NAMED_TRIP_SUFFIXES) and len(tag) >= NAMED_TRIP_MIN_LENGTH)


def is_holy(post, trip_tags):
    return any("聖地" in tag and not is_trip_tag(tag, trip_tags) for tag in post["hashtags"])


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
    trip_tags = {t["tag"] for t in json.loads((JOURNEY / "trips.json").read_text(encoding="utf-8"))["trips"]}
    dictionary = [
        w for w in json.loads(args.out.read_text(encoding="utf-8"))["works"] if not w.get("untitled")
    ]

    holy_posts = [p for p in posts if is_holy(p, trip_tags)]
    holy_ids = {p["id"] for p in holy_posts}
    by_id = {p["id"]: p for p in posts}

    # 1回目：タグの作品名・聖地の場所・個別の指定で作品に入れる
    groups = []
    for entry in dictionary:
        keys = [normalize(k) for k in [entry["title"], *entry.get("aliases", [])]]
        spots = {normalize(s) for s in entry.get("spots", [])}
        for post_id in entry.get("extraPostIds", []):
            if post_id not in by_id:
                print(f"  extraPostIds に該当する投稿が無い（載せない投稿を含む）: {entry['title']} {post_id}")
        group = [
            p for p in posts
            if (p["id"] in holy_ids and any(k in normalize(t) for k in keys for t in p["hashtags"]))
            or spots & {normalize(t) for t in p["hashtags"]}
            or p["id"] in entry.get("extraPostIds", [])
        ]
        groups.append(group)
    direct = collections.defaultdict(set)  # 投稿ID → 1回目で入った作品（dictionary の添字）
    for index, group in enumerate(groups):
        for p in group:
            direct[p["id"]].add(index)

    # 2回目：残った聖地巡礼の投稿の作品を、同じ日→同じ旅の投稿から推し量る（2026-10-15 本人の指示）
    by_day = collections.defaultdict(list)
    for p in posts:
        if p["date_precision"] == "day":
            by_day[p["date"]].append(p)
    trips = json.loads((JOURNEY / "trips.json").read_text(encoding="utf-8"))["trips"]
    # 旅のタグの組と、期間つきの旅（window）なら期間。期間の外の同じタグの投稿は同じ旅に数えない
    trip_sets = [({t["tag"], *t.get("spots", [])}, (t["start"], t["end"]) if t.get("window") else None) for t in trips]

    def within(post, span):
        return span is None or span[0] <= post["date"] <= span[1]

    def works_of(neighbors, post_id):
        return {i for q in neighbors if q["id"] != post_id for i in direct.get(q["id"], ())}

    inferred = collections.defaultdict(dict)  # 作品の添字 → {投稿ID: 同じ日／同じ旅}
    candidates = {}  # 決められなかった投稿ID → {scope, titles}
    for p in holy_posts:
        if p["id"] in direct:
            continue
        found, scope = works_of(by_day.get(p["date"], []) if p["date_precision"] == "day" else [], p["id"]), "同じ日"
        if not found:
            tags = set(p["hashtags"])
            mates = [
                q for q in posts
                if any(tags & ts and within(p, span) and set(q["hashtags"]) & ts and within(q, span) for ts, span in trip_sets)
            ]
            found, scope = works_of(mates, p["id"]), "同じ旅"
        if len(found) == 1:
            index = next(iter(found))
            groups[index].append(p)
            inferred[index][p["id"]] = scope
        elif found:
            candidates[p["id"]] = {"scope": scope, "titles": sorted(dictionary[i]["title"] for i in found)}

    order = {p["id"]: n for n, p in enumerate(posts)}
    works, rest, assigned = [], [], set()
    for index, (entry, group) in enumerate(zip(dictionary, groups)):
        group = sorted(group, key=lambda p: order[p["id"]])  # 推し量った投稿も posts.json の並びに戻す
        assigned.update(p["id"] for p in group)
        record = {k: entry[k] for k in ("slug", "title", "aliases", "spots", "extraPostIds") if k in entry}
        if inferred.get(index):
            record["inferred"] = inferred[index]
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
        record = {**UNTITLED, "candidates": candidates} if candidates else UNTITLED
        works.append(summarize(record, untitled, resolved))
    args.out.write_text(
        json.dumps({"works": works + rest}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    print(f"{args.out} に作品 {sum(1 for w in works if not w.get('untitled'))} 件（聖地巡礼に数える投稿 {len(holy_ids | assigned)} 件）")
    pref = {p["code"]: p["name"] for p in json.loads((ROOT / "data" / "ontology" / "prefectures.json").read_text(encoding="utf-8"))}
    for w in works:
        where = "/".join(pref[c] for c in w["prefCodes"][:3])
        print(f"  {w['postCount']:3d}投稿  {w['start']}〜{w['end']}  {where:<18} {w['title']}")
    for w in rest:
        print(f"  （{'除外' if w.get('hidden') else '投稿なし'}）{w['postCount']:3d}投稿  {w['title']}")
    for index, found in inferred.items():
        print(f"  作品を推し量った {len(found)} 件 → {dictionary[index]['title']}（{'・'.join(sorted(set(found.values())))}の投稿から）")
    for post_id, c in candidates.items():
        print(f"  作品を決められない（{c['scope']}の投稿に {'・'.join(c['titles'])}）: {by_id[post_id]['date']} {post_id}")
    if untitled:
        print(f"\n  作品名なし {len(untitled)} 件（作品なら works に title・aliases を足す）:")
        for p in untitled[:8]:
            print(f"    {p['date']}  {' '.join('#' + t for t in p['hashtags'][:8])}")


if __name__ == "__main__":
    main()
