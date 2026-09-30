#!/usr/bin/env python3
"""文字だけの県判定がどれだけ当たるかを測る。

Instagram API は位置情報を返さないので、同期で入る新着は GPS も人の指定も無いまま
本文とタグだけで県が決まる。その条件で全件を判定し直し、県が確かめられている投稿と
突き合わせる。判定ルールを変えるときは、変える前に --save、変えた後に --compare で
直った投稿と壊れた投稿を確かめる。

正解は resolved.json から取る（gps.json は読まない。手元でも Actions でも動く）:
  人の指定（method: override）があればその県、無ければ GPS の県（gpsPrefCode）
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gazetteer import Gazetteer  # noqa: E402
from resolve import find_override, inherit, resolve_caption_places, resolve_post  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"


def labels(resolved):
    """人か GPS で県が確かめられた投稿だけを正解にする。"""
    truth = {}
    for post_id, r in resolved.items():
        if r.get("method") == "override" and r.get("prefCodes"):
            truth[post_id] = r["prefCodes"]
        elif r.get("gpsPrefCode"):
            truth[post_id] = [r["gpsPrefCode"]]
    return truth


def predict(posts, gaz):
    """新着と同じ条件で判定する。GPS と投稿IDの指定は使わず、タグの指定（新着にも効く）は使う。"""
    results = {}
    for post in posts:
        override = find_override(post, gaz, {})
        if override is not None:
            results[post["id"]] = {"prefCodes": override[0], "method": "override", "evidence": override[1]}
            continue
        codes, method, evidence = resolve_post(post, gaz, {})
        if not codes:
            codes, method, evidence = resolve_caption_places(post, gaz)
        results[post["id"]] = {"prefCodes": codes, "method": method, "evidence": evidence}
    inherit(posts, results)
    return results


def grade(predicted, truth):
    if not predicted:
        return "none"
    return "ok" if set(predicted) & set(truth) else "wrong"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--save", type=pathlib.Path, help="投稿ごとの結果を保存する（ルールを変える前に）")
    parser.add_argument("--compare", type=pathlib.Path, help="保存した結果と比べて、直った・壊れた投稿を出す")
    parser.add_argument("--errors", type=int, default=0, help="誤りの例をこの件数だけ出す")
    args = parser.parse_args()

    posts = json.loads((JOURNEY / "posts.json").read_text(encoding="utf-8"))["posts"]
    resolved = json.loads((JOURNEY / "resolved.json").read_text(encoding="utf-8"))["posts"]
    truth = labels(resolved)
    predicted = predict(posts, Gazetteer())
    by_id = {p["id"]: p for p in posts}

    grades = {i: grade(predicted[i]["prefCodes"], truth[i]) for i in truth}
    count = collections.Counter(grades.values())
    total = len(grades)
    print(f"正解のある投稿 {total} 件（人の指定か GPS で県が確かめられたもの）")
    for key, name in (("ok", "正解"), ("wrong", "誤り"), ("none", "決まらない")):
        print(f"  {name:<5} {count[key]:4d}  ({count[key] / total:.1%})")

    print("\n  根拠別（決まった件数・誤り・正解率）:")
    per_method = collections.defaultdict(collections.Counter)
    for i, g in grades.items():
        if g != "none":
            per_method[predicted[i]["method"]][g] += 1
    for method, c in sorted(per_method.items(), key=lambda kv: -sum(kv[1].values())):
        decided = c["ok"] + c["wrong"]
        print(f"    {method:<20} {decided:4d}  誤り {c['wrong']:3d}  {c['ok'] / decided:.0%}")

    def show(post_id):
        p, r = by_id[post_id], predicted[post_id]
        head = " / ".join(line for line in p["caption"].splitlines()[:2] if line.strip())[:48]
        return f"{p['date']} {post_id} {r['prefCodes']} ← {r['method']}「{r['evidence']}」 正解 {truth[post_id]} | {head}"

    if args.errors:
        print(f"\n  誤りの例（{args.errors} 件まで）:")
        for post_id in [i for i, g in grades.items() if g == "wrong"][: args.errors]:
            print("    " + show(post_id))

    if args.compare:
        before = json.loads(args.compare.read_text(encoding="utf-8"))
        fixed = [i for i, g in grades.items() if g == "ok" and before.get(i) != "ok"]
        broken = [i for i, g in grades.items() if g != "ok" and before.get(i) == "ok"]
        print(f"\n  前回から: 直った {len(fixed)} 件 / 壊れた {len(broken)} 件")
        for post_id in broken:
            print("    壊れた " + show(post_id))

    if args.save:
        args.save.write_text(json.dumps(grades, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
