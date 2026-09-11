"""都道府県マスタと市区町村 -> 都道府県 の対応表を Wikidata から作る。

オントロジー全体の土台。地名の所在地を遡るとき、この表に載っている単位で
止めることで「国立公園や地方まで遡って東北6県が全部ヒットする」事故を防ぐ。

絞り込みには全国地方公共団体コード（Wikidata の P429）を使う。
クラスID（市/町/村/特別区…）を列挙する方式はクラス体系の揺れに弱いが、
団体コードは総務省が定める公式の識別子なので、これを持つことが
「日本の市区町村である」ことの十分に確かな証拠になる。

さらに県の同定にも名前ではなく団体コードの先頭2桁を使う。ラベルで突き合わせると
「東京府」のような歴史上の行政区画が混入するが、コードなら 01〜47 に必ず収まる。
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sparql import qid, run  # noqa: E402

OUT_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "ontology"

# 都道府県そのもの。団体コードは 010006（北海道）のように6桁で、先頭2桁が県コード
PREFECTURES = """
SELECT ?pref ?prefLabel ?prefEn ?code WHERE {
  ?pref wdt:P31 wd:Q50337 ;
        wdt:P429 ?code .
  ?pref rdfs:label ?prefLabel   FILTER(lang(?prefLabel) = "ja")
  OPTIONAL { ?pref rdfs:label ?prefEn FILTER(lang(?prefEn) = "en") }
}
"""

MUNICIPALITIES = """
SELECT ?unit ?unitLabel ?code WHERE {
  ?unit wdt:P429 ?code .
  ?unit wdt:P131* ?pref .
  ?pref wdt:P31 wd:Q50337 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ja". }
}
"""


def build_prefectures() -> dict[str, dict]:
    """県コード2桁 -> 県情報。01〜47 に収まらないものは歴史上の区画として捨てる。"""
    print("都道府県を取得中 ...")
    rows = run(PREFECTURES)

    prefs: dict[str, dict] = {}
    for row in rows:
        code = row.get("code", "")[:2]
        if not (code.isdigit() and 1 <= int(code) <= 47):
            continue
        # 同じコードに複数エンティティが来たら、先に来たものを採る
        prefs.setdefault(
            code,
            {
                "code": code,
                "qid": qid(row["pref"]),
                "name": row.get("prefLabel", ""),
                "en": row.get("prefEn", ""),
            },
        )

    print(f"  {len(prefs)} prefectures")
    return prefs


def build_municipalities(prefs: dict[str, dict]) -> list[dict]:
    print("市区町村を取得中 (P429 = 全国地方公共団体コード) ...")
    rows = run(MUNICIPALITIES)
    print(f"  {len(rows)} rows")

    table: dict[str, dict] = {}
    skipped = 0
    for row in rows:
        code = row.get("code", "")
        pref_code = code[:2]
        if pref_code not in prefs:
            skipped += 1
            continue
        table.setdefault(
            qid(row["unit"]),
            {
                "qid": qid(row["unit"]),
                "name": row.get("unitLabel", ""),
                "code": code,
                "prefCode": pref_code,
            },
        )

    if skipped:
        print(f"  県コードが 01-47 に収まらない {skipped} 行を除外")
    return sorted(table.values(), key=lambda u: u["code"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prefs = build_prefectures()
    pref_list = sorted(prefs.values(), key=lambda p: p["code"])
    (OUT_DIR / "prefectures.json").write_text(
        json.dumps(pref_list, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    units = build_municipalities(prefs)
    (OUT_DIR / "municipalities.json").write_text(
        json.dumps(units, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    covered = {u["prefCode"] for u in units}
    print(f"\nwrote {len(pref_list)} prefectures, {len(units)} municipalities -> {OUT_DIR}")
    print(f"  市区町村を持つ県: {len(covered)} / 47")
    missing = sorted(set(prefs) - covered)
    if missing:
        print(f"  ⚠ 市区町村が1件も取れなかった県: {[prefs[c]['name'] for c in missing]}")


if __name__ == "__main__":
    main()
