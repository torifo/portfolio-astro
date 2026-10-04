#!/usr/bin/env python3
"""Instagram 同期の PR 本文を作る。

基準（既定は origin/main）と作業ツリーの data/journey を比べ、新着の投稿・旅の
変化・自動の点検結果・直し方を Markdown で書く。open_sync_prs.sh（Actions）と auto_sync.sh（手元）が PR を作るときに使う。

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
from resolve import date_line_text, resolve_post  # noqa: E402

# build_trips.py の NAMED_TRIP_* と同じ見分け方（片方だけ変えると判定が食い違う）
TRIP_SUFFIXES = ("旅", "編", "旅行", "ツアー", "巻")
TRIP_MIN_LENGTH = 8
# 同じ撮影日のほかの投稿がこの件数以上あり、この割合以上が同じ県なら、その県と違う新着を指摘する
SAME_DAY_MIN = 2
SAME_DAY_SHARE = 0.6
# 人が県を決めた根拠。県の食い違いの点検（同じ日・旅の主な県）はしない
DECIDED_BY_PERSON = ("override", "date-line-place", "date-line-hidden")
# 撮影日が年まで・不明の投稿（date_overrides.json の "2022" / "unknown"）。同じ日・旅の期間の点検に使わない
UNDATED = ("year", "unknown")
# 自動マージしてよい根拠（本人が日付の後ろに書いた場所、または「趣味」＝載せない）
AUTO_MERGE_METHODS = ("date-line-place", "date-line-hidden")
METHOD_LABELS = {
    "override": "手動指定",
    "pref-name": "県名タグ",
    "pref-name-caption": "本文の県名",
    "curated": "辞書",
    "ontology": "地名",
    "ontology-substring": "地名（部分一致）",
    "gps": "GPS",
    "gps-over-tag": "GPS（タグと不一致）",
    "trip-inherit": "旅から継承",
    "caption-place": "本文の地名",
    "date-line-place": "日付の後ろの場所",
    "date-line-hidden": "日付の後ろの「趣味」",
    "border-gps": "県境（GPS）",
    "border-majority": "県境（同じ場所の GPS の多い県）",
}


def load(root, rel):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def load_base(root, ref, rel):
    out = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{rel}"], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def first_line(post):
    lines = (post.get("caption") or "").replace("⁡", "").splitlines()
    if date_line_text(post):
        lines = lines[1:]  # 日付の行の続きは場所なので、題は次の行から取る
    for line in lines:
        line = line.strip()
        # 日付やタグだけの行を投稿名にしない。
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
    codes, method, evidence = resolve_post(stripped, gaz, {})
    if codes and set(codes) != set(resolved.get("prefCodes") or []):
        # 部分一致の候補を確かな地名と誤解させない。
        partial = method in ("pref-name-caption", "ontology-substring")
        return codes, evidence + ("（部分一致）" if partial else "")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, required=True, help="取り込みを済ませた作業ツリー")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--repo", required=True, help="owner/name（サムネイルの URL に使う）")
    parser.add_argument("--sha", required=True, help="サムネイルを指すコミット")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--summary", type=pathlib.Path, required=True, help="件数を JSON で書く")
    parser.add_argument("--notes", type=pathlib.Path, help="PR で直した内容の Markdown ファイル")
    parser.add_argument("--preface", help="件数の直後に入れる段落")
    args = parser.parse_args()

    root = args.root
    posts = {p["id"]: p for p in load(root, "data/journey/posts.json")["posts"]}
    base_posts = {p["id"] for p in load_base(root, args.base, "data/journey/posts.json")["posts"]}
    resolved = load(root, "data/journey/resolved.json")["posts"]
    base_resolved = load_base(root, args.base, "data/journey/resolved.json")["posts"]
    trips = load(root, "data/journey/trips.json")["trips"]
    works = [w for w in load(root, "data/journey/pilgrimages.json")["works"] if w.get("postCount") and not w.get("hidden")]
    base_trips = {t["tag"]: t for t in load_base(root, args.base, "data/journey/trips.json")["trips"]}
    permalinks = load(root, "data/journey/permalinks.json")
    prefs = {p["code"]: p["name"] for p in load(root, "data/ontology/prefectures.json")}
    visited = {
        p["code"] for region in load(root, "data/journey/prefectures.json")["regions"] for p in region["prefectures"] if p["visited"]
    }

    new = sorted((posts[i] for i in posts if i not in base_posts), key=lambda p: (p["date"], p["id"]))
    base_count = collections.Counter(c for r in base_resolved.values() for c in (r.get("prefCodes") or []))
    trip_of_tag = {t["tag"]: t for t in trips if not t.get("hidden")}

    gaz = Gazetteer()
    trip_tags = {t["tag"] for t in trips}
    by_date = collections.defaultdict(list)
    for post_id, post in posts.items():
        if post.get("date_precision") not in UNDATED:
            by_date[post["date"]].append(post_id)

    def same_day_majority(post):
        """同じ日のほかの投稿の多くが一つの県なら (県コード, 件数, 母数)。旅に入らない単発の投稿の誤りを拾う。"""
        others = [resolved[i]["prefCodes"] for i in by_date[post["date"]] if i != post["id"] and resolved[i].get("prefCodes")]
        if len(others) < SAME_DAY_MIN:
            return None
        code, hits = collections.Counter(c for codes in others for c in set(codes)).most_common(1)[0]
        return (code, hits, len(others)) if hits / len(others) >= SAME_DAY_SHARE else None

    def pref_names(codes):
        return "・".join(prefs[c] for c in codes) or "（未解決）"

    def trip_period(trip):
        return trip["start"] if trip["start"] == trip["end"] else f"{trip['start']}〜{trip['end']}"

    warnings = []
    for p in new:
        r = resolved[p["id"]]
        if r.get("hidden"):
            continue  # 載せないと本人が決めた投稿は点検しない
        codes = r.get("prefCodes") or []
        if not codes:
            warnings.append((p, "県が不明", "タグ・本文から県を特定できない"))
        for c in codes:
            # 日付の後ろに書いた県が訪問済み（prefectures.json）なら、最初の投稿でも本人の指定どおりとみなす
            if base_count[c] == 0 and not (r.get("method") == "date-line-place" and c in visited):
                warnings.append((p, "初めての県", f"{prefs[c]}の最初の投稿。撮影地を確認"))
        other = decided_by_trip_tag(p, r, gaz, trip_tags)
        if other:
            alt, evidence = other
            warnings.append(
                (
                    p,
                    "旅タグで県を判定",
                    f"「{r['evidence']}」で{pref_names(codes)}になったが、旅タグを除くと「{evidence}」から{pref_names(alt)}",
                )
            )
        majority = same_day_majority(p) if codes and r.get("method") not in DECIDED_BY_PERSON else None
        if majority and majority[0] not in codes:
            code, hits, total = majority
            warnings.append((p, "同じ日の投稿と県が違う", f"同じ日の{total}件中{hits}件は{prefs[code]}"))
        written = date_line_text(p)
        if written and r.get("method") not in DECIDED_BY_PERSON:
            warnings.append((p, "日付の後ろの場所を読めない", f"「{written}」から県を決められない"))
        if p.get("date_source") == "upload":
            warnings.append((p, "撮影日が不明", "本文に日付が無いため、投稿日を使用"))
        for tag in p["hashtags"] or []:
            trip = trip_of_tag.get(tag)
            if not trip:
                continue
            if p.get("date_precision") not in UNDATED and not (trip["start"] <= p["date"] <= trip["end"]):
                warnings.append(
                    (p, "旅の期間外", f"旅「{trip['title'][:24]}」は {trip_period(trip)}")
                )
            # 新着込みで組み直した旅と比べると新着自身で一致してしまうので、main の旅と比べる。人が決めた県は点検しない
            known = base_trips.get(tag, trip)
            if codes and r.get("method") not in DECIDED_BY_PERSON and not set(codes) & set(known["prefCodes"]):
                warnings.append(
                    (p, "旅の主な県と不一致", f"旅「{trip['title'][:24]}」の主な県は{pref_names(known['prefCodes'])}")
                )

    thumb = f"https://raw.githubusercontent.com/{args.repo}/{args.sha}/public/journey/thumbs/{{}}.webp"
    # 要確認は点検の数ではなく投稿の数で数える（表の行数と合わせる）
    review_ids = {p["id"] for p, _, _ in warnings}
    review_count = len(review_ids)
    auto_ids = [p["id"] for p in new if resolved[p["id"]]["method"] in AUTO_MERGE_METHODS and p["id"] not in review_ids]
    auto_id_set = set(auto_ids)
    hold_ids = [p["id"] for p in new if p["id"] not in auto_id_set]
    # 新着がすべて日付の後ろに書いた場所で決まり、要確認も無ければ、人が見る点が無いのでマージまで進めてよい
    auto_merge = bool(auto_ids) and not hold_ids
    lines = [f"新着 **{len(new)} 件**・要確認 **{review_count} 件**", ""]
    if args.preface:
        lines += [args.preface, ""]

    if warnings:
        lines += ["## 要確認", "", "| | 投稿 | 点検内容 |", "|---|---|---|"]
        checks_by_post = collections.defaultdict(list)
        for p, head, detail in warnings:
            checks_by_post[p["id"]].append(f"**{head}**：{detail}")
        for post_id, checks in checks_by_post.items():
            p = posts[post_id]
            link = permalinks.get(p["id"], "")
            lines.append(
                f'| <img src="{thumb.format(p["id"])}" width="64"> | [{first_line(p)}]({link})<br>`{p["id"]}` '
                f"| {'<br>'.join(checks)} |"
            )
        lines.append("")

    groups = collections.defaultdict(list)
    for p in new:
        tag = next((tag for tag in p["hashtags"] or [] if tag in trip_of_tag), None)  # 旅タグが2つあれば先に付いた方
        groups[("trip", tag) if tag is not None else ("date", p["date"])].append(p)
    lines += [f"## 新着 {len(new)} 件", ""]
    for (kind, key), group in sorted(groups.items(), key=lambda item: item[1][0]["date"]):
        if kind == "trip":
            trip = trip_of_tag[key]
            heading = f"{trip['title']}（{trip_period(trip)}・新着 {len(group)} 件）"
        else:
            heading = f"{key}（旅に入らない投稿）"
        lines += [f"### {heading}", "", "| | 日付 | 内容 | 県 | 根拠 |", "|---|---|---|---|---|"]
        for p in group:
            r = resolved[p["id"]]
            link = permalinks.get(p["id"], "")
            date = p["date"] + ("" if p.get("date_source") != "upload" else " ※")
            lines.append(
                f'| <img src="{thumb.format(p["id"])}" width="64"> | {date} | [{first_line(p)}]({link})<br>`{p["id"]}` '
                f"| {'（載せない）' if r.get('hidden') else pref_names(r.get('prefCodes') or [])} "
                f"| {METHOD_LABELS.get(r['method'], r['method'])} |"
            )
        lines.append("")
    if any(p.get("date_source") == "upload" for p in new):
        lines += ["※ 本文に日付が無いため、投稿日を撮影日として使用。", ""]

    trip_lines = []
    now = {t["tag"]: t for t in trips}
    for tag, t in now.items():
        old = base_trips.get(tag)
        if old is None:
            trip_lines.append(f"- 新規：**{t['title']}**（{trip_period(t)}・{t['postCount']}件・`{t['slug']}`）")
        elif old["postCount"] != t["postCount"] or (old["start"], old["end"]) != (t["start"], t["end"]):
            trip_lines.append(
                f"- 更新：{t['title']}　{old['postCount']}件 → {t['postCount']}件（{trip_period(t)}）"
            )
    for tag, old in base_trips.items():
        if tag not in now:
            trip_lines.append(f"- **無くなった旅**：{old['title']}（`{old['slug']}` の URL が消える）")
    if trip_lines:
        lines += ["## 旅の変化", ""] + trip_lines + [""]

    # 聖地巡礼に入った新着と作品。作品名なしなら、作品として pilgrimages.json の works に足すかを決める
    holy_lines = []
    for p in new:
        titles = [w["title"] for w in works if p["id"] in w["postIds"]]
        if titles:
            holy_lines.append(f"- [{first_line(p)}]({permalinks.get(p['id'], '')})：{'・'.join(titles)}")
    if holy_lines:
        lines += ["## 聖地巡礼", ""] + holy_lines + [""]

    lines += [
        "<details>",
        "<summary>直すとき</summary>",
        "",
        "このブランチで修正し、push してからマージする。",
        "",
        "- 県が違う：`data/journey/overrides.json` に `\"投稿ID\": [\"県コード\"]`",
        "- 撮影日が違う：`data/journey/date_overrides.json` に `\"投稿ID\": \"YYYY-MM-DD\"`（月まで `YYYY-MM`・年まで `YYYY`・不明 `unknown`）",
        "- 修正後に `npm run journey:build` を実行し、コミット",
        "",
        "</details>",
    ]
    if args.notes is not None:
        lines += ["", "## このPRで直したこと", "", args.notes.read_text(encoding="utf-8").strip()]

    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.summary.write_text(
        json.dumps(
            {"new": len(new), "warnings": review_count, "autoMerge": auto_merge, "autoIds": auto_ids, "holdIds": hold_ids},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"新着 {len(new)} 件 / 要確認 {review_count} 件 / 自動マージ {'する' if auto_merge else 'しない'}")


if __name__ == "__main__":
    main()
