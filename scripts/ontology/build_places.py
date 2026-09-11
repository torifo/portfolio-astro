"""地名オントロジー（地名 -> 都道府県・種別）を Wikidata から作る。

所在地は P131 を「1ホップだけ」辿り、行き先が market_municipalities.json に載っている
市区町村であることを要求する。再帰的に遡ると国立公園や地方まで到達して
「乳頭温泉郷 -> 東北6県」のような誤りが出るため、ここは意図的に浅くしている。

県が複数ついた場合、原因は2種類あって扱いが違う。この区別は index 側で行う:
  - またがり : 同一 QID が複数の市区町村に属する（白神山地 = 青森・秋田）-> 全部正しい
  - 同名異所 : 別々の QID が同じ名前を持つ（厳島神社が全国に）-> どれか1つのはず
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from kinds import KINDS  # noqa: E402
from sparql import qid, run  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "ontology"
PARTIAL = OUT_DIR / ".places-partial"

CHUNK = 40  # 1クエリあたりの市区町村数。増やすと Wikidata の60秒制限に当たる

TEMPLATE = """
SELECT ?item ?name ?alias ?kind ?sitelinks WHERE {{
  VALUES ?muni {{ {munis} }}
  VALUES ?kind {{ {kinds} }}
  ?item wdt:P131 ?muni ;
        wdt:P31/wdt:P279* ?kind ;
        wikibase:sitelinks ?sitelinks ;
        rdfs:label ?name .
  FILTER(lang(?name) = "ja")
  OPTIONAL {{ ?item skos:altLabel ?alias FILTER(lang(?alias) = "ja") }}
}}
"""

KIND_VALUES = " ".join(f"wd:{q}" for q in KINDS)


def fetch_prefecture(pref_code: str, munis: list[dict]) -> dict[str, dict]:
    """1県分の場所を取る。市区町村ごとに県コードを引けるよう対応表を渡す。"""
    by_qid = {m["qid"]: m for m in munis}
    places: dict[str, dict] = {}

    for i in range(0, len(munis), CHUNK):
        chunk = munis[i : i + CHUNK]
        query = TEMPLATE.format(
            munis=" ".join(f"wd:{m['qid']}" for m in chunk), kinds=KIND_VALUES
        )
        rows = run(query)
        for row in rows:
            item = qid(row["item"])
            entry = places.setdefault(
                item,
                {
                    "qid": item,
                    "name": row["name"],
                    "aliases": [],
                    "prefCodes": [pref_code],
                    "kinds": [],
                    "sitelinks": int(row.get("sitelinks", 0)),
                },
            )
            kind = KINDS.get(qid(row["kind"]))
            if kind and kind not in entry["kinds"]:
                entry["kinds"].append(kind)
            alias = row.get("alias")
            if alias and alias != entry["name"] and alias not in entry["aliases"]:
                entry["aliases"].append(alias)

    # by_qid は将来 市区町村名まで持たせたくなったとき用。今は県コードだけで足りる
    del by_qid
    return places


def main() -> None:
    munis = json.loads((OUT_DIR / "municipalities.json").read_text(encoding="utf-8"))
    by_pref: dict[str, list[dict]] = {}
    for m in munis:
        by_pref.setdefault(m["prefCode"], []).append(m)

    PARTIAL.mkdir(parents=True, exist_ok=True)
    all_places: dict[str, dict] = {}

    for n, pref_code in enumerate(sorted(by_pref), 1):
        cache = PARTIAL / f"{pref_code}.json"
        if cache.exists():  # 途中で落ちても取り直しにならないようにする
            places = json.loads(cache.read_text(encoding="utf-8"))
            print(f"[{n:>2}/47] {pref_code} cached ({len(places)})")
        else:
            places = fetch_prefecture(pref_code, by_pref[pref_code])
            cache.write_text(json.dumps(places, ensure_ascii=False), encoding="utf-8")
            print(f"[{n:>2}/47] {pref_code} {len(places):>5} places "
                  f"({len(by_pref[pref_code])} municipalities)")

        for item, entry in places.items():
            if item in all_places:
                # 同じ QID が複数県に出る = 県境をまたぐ実体
                for pc in entry["prefCodes"]:
                    if pc not in all_places[item]["prefCodes"]:
                        all_places[item]["prefCodes"].append(pc)
            else:
                all_places[item] = entry

    out = sorted(all_places.values(), key=lambda p: (-p["sitelinks"], p["name"]))
    (OUT_DIR / "places.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=None), encoding="utf-8"
    )

    spans = [p for p in out if len(p["prefCodes"]) > 1]
    size_mb = (OUT_DIR / "places.json").stat().st_size / 1024 / 1024
    print(f"\nwrote {len(out)} places ({size_mb:.1f} MB) -> {OUT_DIR / 'places.json'}")
    print(f"  県境をまたぐ実体: {len(spans)}")


if __name__ == "__main__":
    main()
