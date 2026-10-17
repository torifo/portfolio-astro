#!/usr/bin/env python3
"""離島の辞書 data/journey/islands.json を作る（本人の指示「離島は可能な限り入れて、利尻とか与那国とか五島列島各島ね」2026-10-18）。

1. 候補の地名（data/ontology/places.json、Wikidata 由来）のうち種類が島の地名から、正式な名前（…島・…諸島・…列島）を拾う
2. 候補に無い・名前が違う主な有人の離島と、よく使う短い呼び方（利尻・与那国・波照間）は、人が書いた一覧（EXTRA）から足す

県を決められない名前は入れない：
- ほかの県に同名の市区町村・県名がある（飛島＝愛知の飛島村、湯島＝東京の湯島）
- ほかの県の同名の場所と有名さ（Wikidata のサイトリンク数）が3倍以上離れていない（金華山＝岐阜にも）
- 全国にいくつもある名前（大島・青島・長島・硫黄島 など。AMBIGUOUS）
短い呼び方を全自動で作ると「大仏」「包丁」「人参」のような一般の言葉が混じったので、短い呼び方は人の一覧にだけ書く。
gazetteer.py が人の辞書（gazetteer.json）の下に読み込み、タグと日付の後ろの場所の両方に効く。作り直すときは npm run journey:islands。
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gazetteer import MUNICIPAL_SUFFIX, Gazetteer, normalize  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "journey" / "islands.json"

SUFFIX = re.compile(r"(列島|諸島|群島|島)$")

# 候補の地名（Wikidata）に島として入っていない・名前が違う主な有人の離島と、よく使う短い呼び方（人が書いた一覧）。
# ほかの県にも同じ名前がある島（大島・黒島・豊島・粟島・神島・向島・青島・姫島 など）は入れない
EXTRA = {
    "01": ["利尻島", "利尻", "礼文島", "礼文", "奥尻島", "奥尻", "天売島", "天売", "焼尻島", "焼尻"],
    "04": ["金華山", "網地島", "田代島", "寒風沢島", "野々島", "浦戸諸島"],
    "06": ["飛島"],
    "13": ["伊豆大島", "利島", "新島", "式根島", "式根", "神津島", "神津", "三宅島", "御蔵島", "御蔵", "八丈島", "八丈", "青ヶ島",
           "小笠原諸島", "小笠原", "父島", "母島", "伊豆諸島"],
    "14": ["江の島", "江ノ島", "猿島", "城ヶ島"],
    "15": ["佐渡島", "佐渡"],
    "17": ["舳倉島", "舳倉", "能登島"],
    "22": ["初島"],
    "23": ["日間賀島", "日間賀", "篠島", "佐久島"],
    "24": ["答志島", "答志", "菅島", "坂手島", "渡鹿野島"],
    "25": ["竹生島", "沖島"],
    "28": ["淡路島", "淡路", "家島", "坊勢島", "坊勢", "沼島"],
    "30": ["友ヶ島"],
    "33": ["犬島", "北木島", "北木", "真鍋島", "真鍋", "白石島", "六島"],
    "34": ["宮島", "厳島", "大久野島", "大久野", "因島", "生口島", "生口", "大崎上島", "大崎下島", "江田島", "倉橋島", "倉橋", "能美島"],
    "35": ["周防大島", "屋代島", "角島", "見島", "祝島"],
    "36": ["伊島", "出羽島"],
    "37": ["小豆島", "直島", "男木島", "男木", "女木島", "女木", "佐柳島", "佐柳", "高見島", "志々島", "伊吹島", "手島", "小手島"],
    "38": ["大三島", "伯方島", "伯方", "興居島", "弓削島", "岩城島", "日振島"],
    "39": ["柏島"],
    "40": ["能古島", "能古", "志賀島", "相島", "玄界島", "玄界", "小呂島", "藍島"],
    "41": ["加唐島", "加唐", "小川島", "神集島"],
    "42": ["壱岐島", "壱岐", "対馬", "五島列島", "五島", "福江島", "久賀島", "奈留島", "奈留", "若松島", "中通島", "中通", "小値賀島",
           "小値賀", "宇久島", "宇久", "野崎島", "頭ヶ島", "椛島", "嵯峨ノ島", "黄島", "赤島", "軍艦島", "端島", "九十九島", "伊王島", "伊王",
           "池島", "生月島", "生月", "平戸島", "的山大島", "鷹島"],
    "43": ["天草", "天草諸島", "天草上島", "天草下島", "湯島", "御所浦島", "御所浦"],
    "44": ["保戸島", "深島"],
    "45": ["島野浦島"],
    "46": ["屋久島", "種子島", "奄美大島", "奄美", "加計呂麻島", "加計呂麻", "請島", "与路島", "喜界島", "喜界", "徳之島", "沖永良部島",
           "沖永良部", "与論島", "与論", "甑島", "上甑島", "下甑島", "中甑島", "口永良部島", "口永良部", "トカラ列島", "吐噶喇列島",
           "諏訪之瀬島", "悪石島", "小宝島", "臥蛇島", "獅子島"],
    "47": ["沖縄本島", "波照間島", "波照間", "石垣島", "宮古島", "西表島", "西表", "竹富島", "竹富", "与那国島", "与那国", "小浜島", "鳩間島",
           "鳩間", "新城島", "由布島", "久米島", "座間味島", "座間味", "阿嘉島", "慶留間島", "渡嘉敷島", "渡嘉敷", "粟国島", "粟国",
           "渡名喜島", "渡名喜", "伊平屋島", "伊平屋", "伊是名島", "伊是名", "伊江島", "伊江", "水納島", "瀬底島", "瀬底", "古宇利島",
           "古宇利", "屋我地島", "屋我地", "伊計島", "浜比嘉島", "平安座島", "平安座", "津堅島", "津堅", "久高島", "久高", "伊良部島",
           "伊良部", "下地島", "来間島", "来間", "池間島", "池間", "大神島", "多良間島", "多良間", "南大東島", "南大東", "北大東島",
           "北大東", "大東諸島", "慶良間諸島", "八重山諸島", "宮古諸島"],
}
# 全国に同名の島・地名がいくつもあり、有名さの差だけで県を決めると誤る名前（大島は奄美大島・周防大島などでも呼ぶ、
# 青島は宮崎、長島はナガシマスパーランドの三重、硫黄島は鹿児島にもある）。人が県を決める
AMBIGUOUS = {"大島", "粟島", "青島", "姫島", "久賀", "長島", "硫黄島", "鳥島", "宝島", "大根", "黒島", "高島", "中島", "小島",
             "竹島", "神島", "向島", "鹿島", "平島", "中之島", "福島", "広島", "本島",
             # 一般の言葉・方角や形だけの名前（離島・無人島・南島・東島・前島・亀島…）
             "離島", "無人島", "人工島", "孤島", "南島", "北島", "東島", "西島", "前島", "後島", "亀島", "岩島", "石島", "裏島"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", type=pathlib.Path, help="公開用（torifo/ritou）の data/ritou.json・ritou.csv・prefectures.csv をこのフォルダに書く")
    args = parser.parse_args()
    gaz = Gazetteer()
    # 全国の地名（種類を問わない）・市区町村の短い呼び方・県名で、その呼び方がどの県を指しうるか。県ごとに一番有名な場所の
    # サイトリンク数を持つ（市区町村・県名は強い印として 999）
    where = collections.defaultdict(lambda: collections.defaultdict(int))
    for place in gaz.places:
        for term in [place["name"], *place.get("aliases", [])]:
            for code in place["prefCodes"]:
                slot = where[normalize(term)]
                slot[code] = max(slot[code], place.get("sitelinks", 0))
    for muni in gaz.municipalities:
        for term in (muni["name"], MUNICIPAL_SUFFIX.sub("", muni["name"])):
            where[normalize(term)][muni["prefCode"]] = 999
    for term, codes in gaz.pref_terms.items():
        for code in codes:
            where[term][code] = 999

    def unique_to(key, code):
        """その呼び方をこの県の島と決めてよいか。ほかの県に同名の市区町村・県名があれば不可。ほかの県の同名の場所は、
        この県の島がサイトリンクで3倍以上有名なら無視する（江の島 33 対 宮城の江島 3、軍艦島 50 対 石川の見附島 13）。
        候補の地名に無い島（人の一覧）は、ほかの県の同名がサイトリンク1以下のときだけ"""
        others = {c: n for c, n in where[key].items() if c != code}
        if not others:
            return True
        top = max(others.values())
        if top >= 999:
            return False
        own = where[key].get(code, 0)
        return (own >= 3 and own >= 3 * top) or (own == 0 and top <= 1)

    islands = [p for p in gaz.places if "島" in p.get("kinds", []) and len(p["prefCodes"]) == 1]
    found, skipped = {}, collections.Counter()
    origin = {}  # 語 → (種類, 出どころ)
    for island in islands:
        code = island["prefCodes"][0]
        # 機械で拾うのは正式な名前（…島・…諸島・…列島）だけ。短い呼び方を全自動で作ると「大仏」「包丁」「人参」のような
        # 一般の言葉が大量に混じった（2026-10-18）ので、短い呼び方は人の一覧（EXTRA）にだけ書く。括弧つきの名前（…島 (埼玉県)）も外す
        forms = {f for f in (island["name"], *island.get("aliases", [])) if SUFFIX.search(f) and "(" not in f and "（" not in f}
        for form in forms:
            key = normalize(form)
            if len(key) < 2 or key in gaz.pref_terms or form in AMBIGUOUS:
                continue
            if not unique_to(key, code):
                skipped["ほかの県にも同じ名前"] += 1
                continue
            found[form] = [code]
            origin[form] = ("name" if form == island["name"] else "alias", f"wikidata:{island['qid']}")

    # 人が書いた一覧。同じ決まりで、決められないものは入れずに知らせる
    extra_skipped = []
    for code, names in EXTRA.items():
        for name in names:
            if name in AMBIGUOUS:
                continue
            if not unique_to(normalize(name), code):
                others = sorted(c for c in where[normalize(name)] if c != code)
                extra_skipped.append(f"{name}（{code}／ほかに {','.join(others)}）")
                continue
            found[name] = [code]
            origin[name] = ("manual", "manual")

    document = {
        "_": "離島の辞書（scripts/journey/build_islands.py が places.json の島から作る。人が直さない）。"
             "島の正式な名前（Wikidata の島）と、人が書いた主な離島・短い呼び方 → 県コード。県を決められない名前は入れない。"
             "人の辞書（gazetteer.json）が勝つ",
        **dict(sorted(found.items())),
    }
    OUT.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT} に {len(found)} 語（島 {len(islands)} 件から）")
    if args.export:
        export(args.export, found, origin, gaz.pref_name)
    for reason, n in skipped.most_common():
        print(f"  入れなかった：{reason} {n}")
    if extra_skipped:
        print("  人の一覧から入れなかった（同名がほかの県にある）：" + "、".join(extra_skipped))


def export(folder, found, origin, pref_name):
    """公開用のデータ。ritou.json は呼び方 → 県コード（文字列）、ritou.csv は出どころつきの表、prefectures.csv は県コードと県名"""
    folder.mkdir(parents=True, exist_ok=True)
    terms = dict(sorted((term, codes[0]) for term, codes in found.items()))
    (folder / "ritou.json").write_text(json.dumps(terms, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    with open(folder / "ritou.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["term", "pref_code", "pref_name", "kind", "source"])
        for term, code in terms.items():
            kind, source = origin[term]
            writer.writerow([term, code, pref_name[code], kind, source])
    with open(folder / "prefectures.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["pref_code", "pref_name"])
        for code in sorted(pref_name):
            writer.writerow([code, pref_name[code]])
    print(f"{folder} に ritou.json・ritou.csv（{len(terms)} 語）・prefectures.csv を書いた")


if __name__ == "__main__":
    main()
