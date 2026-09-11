#!/usr/bin/env python3
"""投稿 -> 都道府県。raw + 辞書 + override の純関数として解く。

層の順序（先に決まったところで確定する）:

  L0 overrides.json  人の手動指定。常に勝つ。空配列 [] は「どの県にも属さない」
                     の意味で、未解決とは区別する（複数箇所の寄せ集め投稿を
                     県ページから外すために使う。テーマ軸からは引ける）
  L1 EXIF GPS        data/journey/gps.json の座標を県境ポリゴンで引く。
                     このファイルは公開しない（撮影地そのものなので）。
                     無ければこの層は黙って飛ばされ、辞書だけで判定が続く
  L2 県名の直接一致  タグとキャプションに「秋田県」「秋田」が出てくる
  L3 gazetteer.json  人が育てる確定辞書
  L4 オントロジー    places.json の索引にタグが載っている
  L4b 部分一致       長い旅タグの中に地名が埋まっている
  L5 旅グループ継承  同じタグを持つ他の投稿が一つの県で一致している
  終端 unresolved

L6 の LLM はこの外側にいる。出力は必ず gazetteer.json を経由してから
サイトに載るので、非定常な判定がビルドに混ざることはない。
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gazetteer import Gazetteer, normalize  # noqa: E402
from geo import Boundaries  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]

# サイトリンク数で本命を決めるときの閾値。片方が桁違いに有名なときだけ倒す。
DOMINANCE_RATIO = 3
DOMINANCE_FLOOR = 5

# 旅グループ継承を許す最小の裏付け数。1件だけの一致では継承しない。
INHERIT_MIN = 2


def decide(entries, gaz):
    """候補エントリ群から県コードを決める。決まらなければ None。

    県で割れたときだけ曖昧とする。「千秋公園」は千秋公園と久保田城の
    2候補が出るがどちらも秋田県なので、曖昧ではない。
    """
    if not entries:
        return None
    pool = gaz.prioritize(entries)

    if len(pool) == 1:
        return list(pool[0]["prefCodes"])  # 県境またぎはそのまま複数返す

    union = set()
    for entry in pool:
        union.update(entry["prefCodes"])
    if len(union) == 1:
        return sorted(union)

    ranked = sorted(pool, key=lambda e: e.get("sitelinks", 0), reverse=True)
    top, second = ranked[0], ranked[1]
    if top.get("sitelinks", 0) >= DOMINANCE_FLOOR and top.get("sitelinks", 0) >= DOMINANCE_RATIO * max(
        second.get("sitelinks", 0), 1
    ):
        return list(top["prefCodes"])
    return None  # 県で割れていて決め手が無い


def find_override(post, gaz, overrides):
    """L0。見つからなければ None を返す。空配列 [] は「県に属さない」という指定。"""
    if post["id"] in overrides:
        return overrides[post["id"]], post["id"]
    for tag in post["hashtags"]:
        value = gaz.overrides.get(normalize(tag))
        if isinstance(value, list):
            return value, tag
    return None


def resolve_post(post, gaz, overrides):
    tags = post["hashtags"]

    # L2 県名の直接一致。タグを先に見る（キャプションより意図が明確）
    for tag in tags:
        codes = gaz.pref_terms.get(normalize(tag))
        if codes:
            return sorted(set(codes)), "pref-name", tag
    for term, codes in gaz.pref_terms.items():
        if term in normalize(post["caption"]):
            return sorted(set(codes)), "pref-name-caption", term

    # L3 人が育てた確定辞書
    for tag in tags:
        key = normalize(tag)
        if key in gaz.curated:
            return gaz.curated[key], "curated", tag

    # L4 オントロジー索引に完全一致
    for tag in tags:
        codes = decide(gaz.lookup(tag), gaz)
        if codes:
            return codes, "ontology", tag

    # L4b 旅タグの中に地名が埋まっている場合を拾う
    for tag in sorted(tags, key=len, reverse=True):
        for term, entries in gaz.find_in(tag):
            codes = decide(entries, gaz)
            if codes:
                return codes, "ontology-substring", f"{tag} ⊃ {term}"

    return None, None, None


def resolve_caption_places(post, gaz):
    """最後の手段としてキャプション本文から地名を拾う。

    本文はタグより雑音が多い（「秋田」と書きながら写真は東京、が実際に起きる）。
    そのため GPS もタグも無い投稿に限って使う。近所の散歩の記録には
    「南大沢駅」「多磨霊園駅」のような地名が本文にしか出てこない。
    """
    for term, entries in gaz.find_in(post["caption"]):
        codes = decide(entries, gaz)
        if codes:
            return codes, "caption-place", term
    return None, None, None


def inherit(posts, results):
    """L5 同じタグを共有する投稿から継承する。

    「旅タグ」を名前の形で見分けようとしない。同じタグを持つ投稿の県が
    一つに揃っているかどうかをデータに決めさせる。散策・自然のような
    汎用タグは県が割れるので、この条件で自動的に脱落する。
    """
    consensus = {}
    by_tag = collections.defaultdict(list)
    for post in posts:
        for tag in post["hashtags"]:
            by_tag[normalize(tag)].append(post["id"])

    for tag, ids in by_tag.items():
        seen = {tuple(results[i]["prefCodes"]) for i in ids if results[i]["prefCodes"]}
        support = sum(1 for i in ids if results[i]["prefCodes"])
        if len(seen) == 1 and support >= INHERIT_MIN:
            consensus[tag] = list(next(iter(seen)))

    filled = 0
    for post in posts:
        if results[post["id"]]["prefCodes"] is not None:
            continue  # [] は「県に属さない」という決定なので上書きしない
        for tag in post["hashtags"]:
            key = normalize(tag)
            if key in consensus:
                results[post["id"]] = {
                    "prefCodes": consensus[key],
                    "method": "trip-inherit",
                    "evidence": tag,
                }
                filled += 1
                break
    return filled


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts", type=pathlib.Path, default=ROOT / "data" / "journey" / "posts.json")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "data" / "journey" / "resolved.json")
    parser.add_argument(
        "--policy",
        choices=("gps", "tag"),
        default="gps",
        help="GPS とタグが食い違ったときにどちらを採るか（既定: gps）",
    )
    parser.add_argument("--report", action="store_true", help="内訳と未解決の一覧を出す")
    args = parser.parse_args()

    posts = json.loads(args.posts.read_text(encoding="utf-8"))["posts"]
    # 座標は公開ファイルから分離してある。無くても辞書だけで動く。
    gps_path = args.posts.with_name("gps.json")
    coordinates = {}
    if gps_path.exists():
        coordinates = {
            key: value
            for key, value in json.loads(gps_path.read_text(encoding="utf-8")).items()
            if not key.startswith("_")
        }
    gaz = Gazetteer()
    boundaries = Boundaries()
    # overrides.json は投稿ID・タグ名のどちらをキーにしてもよい。先頭が _ のキーは覚書。
    overrides = {
        key: value
        for key, value in gaz.overrides.items()
        if not key.startswith("_") and isinstance(value, list)
    }

    results, conflicts = {}, []
    for post in posts:
        # L0 は GPS より先に決まる。空配列の指定もここで確定させる。
        override = find_override(post, gaz, overrides)
        if override is not None:
            codes, evidence = override
            results[post["id"]] = {
                "prefCodes": codes,
                "method": "override",
                "evidence": evidence,
                "tagPrefCodes": codes,
                "gpsPrefCode": None,
            }
            continue

        tag_codes, method, evidence = resolve_post(post, gaz, overrides)

        gps_code = None
        point = coordinates.get(post["id"])
        if point:
            gps_code, _ = boundaries.locate(*point)

        # どちらも決まらなかったときだけ本文を当たる。
        if not tag_codes and not gps_code:
            tag_codes, method, evidence = resolve_caption_places(post, gaz)

        if tag_codes and gps_code and gps_code not in tag_codes:
            conflicts.append(
                {
                    "id": post["id"],
                    "date": post["date"],
                    "caption": " / ".join(post["caption"].splitlines()[:2])[:80],
                    "hashtags": post["hashtags"][:8],
                    "tagPrefCodes": tag_codes,
                    "tagMethod": method,
                    "tagEvidence": evidence,
                    "gpsPrefCode": gps_code,
                }
            )
            if args.policy == "gps":
                codes, chosen = [gps_code], "gps-over-tag"
            else:
                codes, chosen = tag_codes, method
        elif tag_codes:
            codes, chosen = tag_codes, method
        elif gps_code:
            codes, chosen = [gps_code], "gps"
        else:
            codes, chosen = None, None

        results[post["id"]] = {
            "prefCodes": codes,
            "method": chosen,
            # 座標は証跡にも残さない。県コードで十分たどれる。
            "evidence": evidence if chosen != "gps" else gps_code,
            "tagPrefCodes": tag_codes,
            "gpsPrefCode": gps_code,
        }

    inherited = inherit(posts, results)

    resolved = sum(1 for r in results.values() if r["prefCodes"])
    detached = sum(1 for r in results.values() if r["prefCodes"] == [])
    unresolved = sum(1 for r in results.values() if r["prefCodes"] is None)
    total = len(posts)
    print(f"投稿 {total} 件")
    print(f"  県が決まった: {resolved} ({resolved / total:.1%})   ※LLM 呼び出しゼロ")
    if detached:
        print(f"  県に属さない: {detached}（overrides で [] を指定したもの）")
    print(f"  未解決      : {unresolved} ({unresolved / total:.1%})")
    print(f"  うち旅グループ継承で埋まった: {inherited}")

    by_method = collections.Counter(r["method"] for r in results.values() if r["prefCodes"])
    print("\n  内訳:")
    for method, count in by_method.most_common():
        print(f"    {count:4d}  {method}")

    if args.report:
        print("\n  未解決の投稿:")
        for post in posts:
            if not results[post["id"]]["prefCodes"]:
                head = post["caption"].splitlines()[0][:48] if post["caption"] else ""
                gps = "GPS有" if coordinates.get(post["id"]) else "GPS無"
                print(f"    [{post['date']}] {gps} {head}")
                if post["hashtags"]:
                    print(f"            tags: {' '.join('#' + t for t in post['hashtags'][:8])}")

    print(f"\n  GPS とタグの食い違い: {len(conflicts)} 件 -> {args.out.with_name('conflicts.json').name}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"policy": args.policy, "posts": results}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    # 人が裁定して overrides.json に落とすための一覧。
    args.out.with_name("conflicts.json").write_text(
        json.dumps(conflicts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
