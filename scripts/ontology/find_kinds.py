"""オントロジーに含める「種別」の Wikidata クラスIDを実データから特定する。

クラスIDを人間の記憶で決め打ちすると高確率で外す（実際 Q179700 を温泉だと
思い込んで像を取得した）。ここでは検索APIで候補を引き、日本国内の実エンティティが
何件ぶら下がっているかを数えて、使えるクラスだけを残す。
"""

import json
import pathlib
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sparql import USER_AGENT, run  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "ontology" / "kinds.json"

# 旅の投稿に出てきそうな被写体・場所の種別
WANTED = [
    "温泉", "山", "湖", "滝", "河川", "渓谷", "岬", "島", "砂浜",
    "神社", "寺院", "城", "公園", "国立公園", "日本庭園",
    "鉄道駅", "空港", "道の駅", "遊園地", "博物館", "美術館", "水族館", "動物園",
    "展望塔", "橋", "ダム", "灯台", "峠", "湿地", "高原", "洞窟",
    "集落", "温泉街", "旅館", "滝壺", "湾", "半島", "平野", "盆地", "火山",
]


def search(term: str, limit: int = 5) -> list[dict]:
    """wbsearchentities で日本語ラベルから候補クラスを引く。"""
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "wbsearchentities",
            "search": term,
            "language": "ja",
            "uselang": "ja",
            "type": "item",
            "limit": limit,
            "format": "json",
        }
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res).get("search", [])


def count_japanese_instances(qids: list[str]) -> dict[str, int]:
    """各クラスについて、日本の市区町村に属する実エンティティ数を数える。

    実際に中身があるクラスだけを採用したいので、ラベル一致ではなく件数で判断する。
    """
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""
    SELECT ?kind (COUNT(DISTINCT ?item) AS ?n) WHERE {{
      VALUES ?kind {{ {values} }}
      ?item wdt:P31/wdt:P279* ?kind ;
            wdt:P131 ?muni .
      ?muni wdt:P429 ?code .
    }}
    GROUP BY ?kind
    """
    return {r["kind"].rsplit("/", 1)[-1]: int(r["n"]) for r in run(query)}


def main() -> None:
    candidates: dict[str, dict] = {}
    for term in WANTED:
        for hit in search(term):
            candidates.setdefault(
                hit["id"],
                {"qid": hit["id"], "label": hit.get("label", ""),
                 "description": hit.get("description", ""), "searchedAs": term},
            )
    print(f"候補クラス {len(candidates)} 件を検索で収集")

    counts: dict[str, int] = {}
    qids = list(candidates)
    for i in range(0, len(qids), 60):  # 一度に投げすぎるとタイムアウトする
        chunk = qids[i : i + 60]
        print(f"  件数を計測中 {i + 1}-{i + len(chunk)} / {len(qids)}")
        counts.update(count_japanese_instances(chunk))

    kept = []
    for qid_, info in candidates.items():
        n = counts.get(qid_, 0)
        if n >= 20:  # 日本国内に実体がほとんど無いクラスは採らない
            info["count"] = n
            kept.append(info)
    kept.sort(key=lambda k: -k["count"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(kept, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nwrote {len(kept)} kinds -> {OUT}")
    for k in kept[:40]:
        print(f"  {k['count']:>7}  {k['qid']:<10} {k['label']} — {k['description'][:40]}")


if __name__ == "__main__":
    main()
