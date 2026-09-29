#!/usr/bin/env python3
"""Instagram 同期の PR 本文を作る。

基準（既定は origin/main）と作業ツリーの data/journey を比べ、新着の投稿・旅の
変化・自動の点検結果・直し方を Markdown で書く。auto_sync.sh が PR を作るときに使う。

点検は、実際に本番へ出てから見つかった誤りの型をそのまま機械で探すもの。
新着の投稿だけを見る（既存の投稿は一度人が見ているので、毎回同じ指摘を出さない）。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gazetteer import Gazetteer  # noqa: E402
from resolve import resolve_post  # noqa: E402

# 一文まるごとの旅タグ。build_trips.py の NAMED_TRIP_* と同じ見分け方
TRIP_SUFFIXES = ("旅", "編", "旅行", "ツアー", "巻")
TRIP_MIN_LENGTH = 8


def load(root, rel):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def load_base(root, ref, rel):
    out = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{rel}"], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def first_line(caption):
    for line in (caption or "").replace("⁡", "").splitlines():
        line = line.strip()
        # 先頭の日付行とタグだけの行は飛ばす
        if not line or line.startswith("#") or re.fullmatch(r"[\d\-/年月日~〜 ]+", line):
            continue
        return line[:40]
    return "（本文なし）"


def decided_by_trip_tag(post, resolved, gaz, trip_tags):
    """旅タグを除いて判定し直すと別の県になるなら、その県を返す。

    「八景島シーパラ東京湾クルーズ東京タワーてんこ盛り旅」の「東京」のように、旅タグの
    一部が県名として当たることがある。旅タグを除いても同じ県になるなら（秋田観光旅の
    #秋田駅 など）問題ない。除くと手がかりが無くなる場合も、指摘しない（判断材料が無い）。
    """
    if resolved["method"] not in ("pref-name", "pref-name-caption", "ontology-substring"):
        return None
    drop = [t for t in post["hashtags"] or [] if t in trip_tags or (t.endswith(TRIP_SUFFIXES) and len(t) >= TRIP_MIN_LENGTH)]
    if not drop:
        return None
    caption = post.get("caption") or ""
    for tag in drop:
        caption = caption.replace("#" + tag, " ")
    stripped = {**post, "hashtags": [t for t in post["hashtags"] if t not in drop], "caption": caption}
    codes, _, evidence = resolve_post(stripped, gaz, {})
    if codes and set(codes) != set(resolved.get("prefCodes") or []):
        return codes, evidence
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True, help="取り込みを済ませた作業ツリー")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--repo", required=True, help="owner/name（サムネイルの URL に使う）")
    parser.add_argument("--sha", required=True, help="サムネイルを指すコミット")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--summary", type=pathlib.Path, required=True, help="件数を JSON で書く")
    args = parser.parse_args()

    root = args.root
    posts = {p["id"]: p for p in load(root, "data/journey/posts.json")["posts"]}
    base_posts = {p["id"] for p in load_base(root, args.base, "data/journey/posts.json")["posts"]}
    resolved = load(root, "data/journey/resolved.json")["posts"]
    base_resolved = load_base(root, args.base, "data/journey/resolved.json")["posts"]
    trips = load(root, "data/journey/trips.json")["trips"]
    base_trips = {t["tag"]: t for t in load_base(root, args.base, "data/journey/trips.json")["trips"]}
    permalinks = load(root, "data/journey/permalinks.json")
    prefs = {p["code"]: p["name"] for p in load(root, "data/ontology/prefectures.json")}

    new = sorted((posts[i] for i in posts if i not in base_posts), key=lambda p: (p["date"], p["id"]))
    base_count = collections.Counter(c for r in base_resolved.values() for c in (r.get("prefCodes") or []))
    trip_of_tag = {t["tag"]: t for t in trips if not t.get("hidden")}

    gaz = Gazetteer()
    trip_tags = {t["tag"] for t in trips}

    def pref_names(codes):
        return "・".join(prefs[c] for c in codes) or "（未解決）"

    warnings = []  # (投稿, 見出し, 説明)
    for p in new:
        r = resolved[p["id"]]
        codes = r.get("prefCodes") or []
        if not codes:
            warnings.append((p, "県が決まらない", "タグ・本文から都道府県を特定できなかった"))
        for c in codes:
            if base_count[c] == 0:
                warnings.append((p, "初めての県", f"{prefs[c]}に入る最初の投稿。本当にそこで撮ったか"))
        other = decided_by_trip_tag(p, r, gaz, trip_tags)
        if other:
            alt, evidence = other
            warnings.append(
                (
                    p,
                    "旅タグの語で県が決まった",
                    f"「{r['evidence']}」で{pref_names(codes)}になったが、旅タグを除くと「{evidence}」から{pref_names(alt)}",
                )
            )
        if p.get("date_source") == "upload":
            warnings.append((p, "撮影日が不明", "キャプションに日付が無く、投稿した日を撮影日にしている"))
        for tag in p["hashtags"] or []:
            trip = trip_of_tag.get(tag)
            if not trip:
                continue
            if not (trip["start"] <= p["date"] <= trip["end"]):
                warnings.append(
                    (p, "旅の期間から外れた日付", f"旅「{trip['title'][:24]}」は {trip['start']}〜{trip['end']}")
                )
            if codes and not set(codes) & set(trip["prefCodes"]):
                warnings.append(
                    (p, "旅の中で浮いている県", f"旅「{trip['title'][:24]}」の主な県は{pref_names(trip['prefCodes'])}")
                )

    thumb = f"https://raw.githubusercontent.com/{args.repo}/{args.sha}/public/journey/thumbs/{{}}.webp"
    lines = [f"Instagram の新着 **{len(new)} 件**を取り込みました。問題が無ければマージすると本番に出ます。", ""]

    lines += [f"## 要確認 {len(warnings)} 件", ""]
    if warnings:
        lines += ["| | 投稿 | 点検 | 内容 |", "|---|---|---|---|"]
        for p, head, detail in warnings:
            link = permalinks.get(p["id"], "")
            lines.append(
                f'| <img src="{thumb.format(p["id"])}" width="64"> | [{first_line(p.get("caption"))}]({link})<br>`{p["id"]}` '
                f"| **{head}** | {detail} |"
            )
    else:
        lines.append("自動の点検では気になる点はありませんでした。")
    lines.append("")

    lines += [f"## 新着 {len(new)} 件", "", "| | 日付 | 内容 | 県 | 根拠 |", "|---|---|---|---|---|"]
    for p in new:
        r = resolved[p["id"]]
        link = permalinks.get(p["id"], "")
        date = p["date"] + ("" if p.get("date_source") != "upload" else " ※")
        lines.append(
            f'| <img src="{thumb.format(p["id"])}" width="64"> | {date} | [{first_line(p.get("caption"))}]({link}) '
            f"| {pref_names(r.get('prefCodes') or [])} | {r['method']} |"
        )
    lines += ["", "※ はキャプションに日付が無く、投稿した日を撮影日にしているもの。", ""]

    trip_lines = []
    now = {t["tag"]: t for t in trips}
    for tag, t in now.items():
        old = base_trips.get(tag)
        if old is None:
            trip_lines.append(f"- 新しい旅：**{t['title']}**（{t['start']}〜{t['end']}・{t['postCount']}件・`{t['slug']}`）")
        elif old["postCount"] != t["postCount"] or (old["start"], old["end"]) != (t["start"], t["end"]):
            trip_lines.append(
                f"- 変化：{t['title']}　{old['postCount']}件 → {t['postCount']}件（{t['start']}〜{t['end']}）"
            )
    for tag, old in base_trips.items():
        if tag not in now:
            trip_lines.append(f"- **無くなった旅**：{old['title']}（`{old['slug']}` の URL が消える）")
    lines += ["## 旅の変化", ""] + (trip_lines or ["変化なし"]) + [""]

    lines += [
        "## 直すとき",
        "",
        "このブランチに直してから push し、マージする。",
        "",
        "- 県が違う：`data/journey/overrides.json` に `\"投稿ID\": [\"県コード\"]`",
        "- 撮影日が違う：`data/journey/date_overrides.json` に `\"投稿ID\": \"YYYY-MM-DD\"`",
        "- 直したら `npm run journey:build` を流してコミット",
        "",
        "Claude に頼むなら「PR の ○○ を △△ に直して」で通じます。",
    ]

    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.summary.write_text(
        json.dumps({"new": len(new), "warnings": len(warnings)}, ensure_ascii=False), encoding="utf-8"
    )
    print(f"新着 {len(new)} 件 / 要確認 {len(warnings)} 件")


if __name__ == "__main__":
    main()
