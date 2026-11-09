#!/usr/bin/env python3
"""県のページの投稿のヒートマップを作る。市区町村ごとに投稿の数を数え、県の形の上に色の濃さで出す。

撮影地の座標（data/journey/gps.json）は公開しない（.git/info/exclude）。ここで市区町村に丸め、
リポジトリには「投稿 → 市区町村」と、表示用に簡略化した市区町村の形だけを書く（本人が市区町村の粗さを選んだ）。
座標の無い投稿（Instagram から自動で取り込んだ最近の投稿）は、本文の地名から市区町村を引く。

政令指定都市の区は市にまとめる（地名からは区まで決まらないため）。東京23区は区のまま。

入力: 国土数値情報 N03 の市区町村ポリゴン（リポジトリの外。unzip で N03-20260101.geojson を出しておく）
出力: data/journey/post_municipalities.json（投稿ID → 市区町村コード）
      src/lib/prefecture-maps.json（県ごとの県境とエリア。近い市区町村をまとめた「札幌エリア」など）

  python3 scripts/journey/build_municipality_maps.py ~/dev/data/kokudo/N03-20260101.geojson
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ontology"))
sys.path.insert(0, str(ROOT / "scripts" / "journey"))
from build_boundaries import FEATURE_LINE, simplify_polygons  # noqa: E402
from gazetteer import Gazetteer  # noqa: E402

JOURNEY = ROOT / "data" / "journey"
OUT_POSTS = JOURNEY / "post_municipalities.json"
PLACE_COORDS = JOURNEY / "place_coords.json"  # 名所の Wikidata 座標の控え（公開の地名データ）
OUT_MAPS = ROOT / "src" / "lib" / "prefecture-maps.json"

ASSIGN_TOLERANCE = 0.0005  # 判定用の簡略化（度）。約50m
NEAREST_LIMIT_KM = 15.0    # 海岸・港・船上で境界の外に落ちた点を寄せる上限
KM_PER_DEGREE = 111.32
VIEW = 1000                # 表示用の SVG の長辺
DISPLAY_RATIO = 0.0025     # 表示用の簡略化。県の大きさに対する比
MIN_ISLAND_RATIO = 0.01    # これより小さい島は表示から落とす（県の大きさに対する比）
FAR_RATIO = 0.6            # 本土の塊からこれ以上離れた島は、投稿があるときだけ差し込み枠に出す
SUFFIX = re.compile(r"(市|町|村|区)$")


def municipality_of(props):
    """(コード, 名前, 政令指定都市か) を返す。政令指定都市の区は市にまとめる（コードは後で市のものに付け替える）。所属未定地は捨てる。"""
    code = props.get("N03_007")
    city = props.get("N03_004")
    if not code or not city or city == "所属未定地":
        return None
    ward = props.get("N03_005")
    if ward and city.endswith("市"):
        return code, city, True
    return code, city, False


def read_municipalities(path):
    """市区町村コード → {name, pref, polygons, designated}。N03 は1行1フィーチャなので行ごとに読む。
    政令指定都市は区をまとめ、いちばん若い区のコードの一の位を0にした市のコードにする（札幌 01101〜01110 → 01100、
    川崎 14131〜 → 14130）。区のコードの上4桁で決めると、清田区 01110 や横浜の 14110〜 が別の市になった"""
    munis, wards = {}, {}
    with path.open("rb") as handle:
        for line in handle:
            match = FEATURE_LINE.match(line)
            if not match:
                continue
            feature = json.loads(match.group(1))
            found = municipality_of(feature["properties"])
            if not found:
                continue
            code, name, designated = found
            polygons = simplify_polygons(feature["geometry"], ASSIGN_TOLERANCE)
            if designated:
                ward = wards.setdefault((code[:2], name), {"codes": set(), "polygons": []})
                ward["codes"].add(code)
                ward["polygons"].extend(polygons)
                continue
            entry = munis.setdefault(code, {"name": name, "pref": code[:2], "polygons": [], "designated": False})
            entry["polygons"].extend(polygons)
    for (pref, name), ward in wards.items():
        city = f"{int(min(ward['codes'])) // 10 * 10:05d}"
        munis[city] = {"name": name, "pref": pref, "polygons": ward["polygons"], "designated": True}
    for entry in munis.values():
        entry["bbox"] = bbox_of(ring for polygon in entry["polygons"] for ring in polygon[:1])
    return munis


def bbox_of(rings):
    xs, ys = [], []
    for ring in rings:
        xs.extend(p[0] for p in ring)
        ys.extend(p[1] for p in ring)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)


def in_ring(lon, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def contains(entry, lon, lat):
    x0, y0, x1, y1 = entry["bbox"]
    if not (x0 <= lon <= x1 and y0 <= lat <= y1):
        return False
    for polygon in entry["polygons"]:
        if in_ring(lon, lat, polygon[0]) and not any(in_ring(lon, lat, hole) for hole in polygon[1:]):
            return True
    return False


def distance_km(entry, lon, lat):
    scale = math.cos(math.radians(lat))
    best = float("inf")
    for polygon in entry["polygons"]:
        ring = polygon[0]
        for (ax, ay), (bx, by) in zip(ring, ring[1:]):
            ax, bx, px = ax * scale, bx * scale, lon * scale
            dx, dy = bx - ax, by - ay
            t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (lat - ay) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(px - (ax + t * dx), lat - (ay + t * dy)))
    return best * KM_PER_DEGREE


def locate(munis, lat, lon, prefs):
    """座標 → 市区町村コード。判定した県の中から探し、境界の外なら最近傍（15km 以内）に寄せる。"""
    pool = [c for c, e in munis.items() if not prefs or e["pref"] in prefs]
    for code in pool:
        if contains(munis[code], lon, lat):
            return code
    near = [(distance_km(munis[c], lon, lat), c) for c in pool]
    near = [n for n in near if n[0] <= NEAREST_LIMIT_KM]
    return min(near)[1] if near else None


SHORT_TAG = 10  # これより長いハッシュタグは旅の名前（「…鳴門海峡祖谷…小豆島巡礼旅」）なので地名探しに使わない


def body_of(post):
    """日付の行とハッシュタグを除いた本文。地名はたいてい日付の次の行にある。"""
    lines = (post.get("caption") or "").splitlines()
    kept = [line for line in lines if not re.match(r"^\s*\d{4}-\d{2}-\d{2}", line)]
    return re.sub(r"#\S+", " ", "\n".join(kept))


def short_tags_of(post):
    return " ".join(tag for tag in (post.get("hashtags") or []) if len(tag) <= SHORT_TAG)


# 島や地域の名前と同じ略し方になる町。「小豆島」は島（土庄町と小豆島町）のことなので、小豆島町は「小豆島町」と書いてあるときだけ当てる
# （#小豆島 が小豆島町に当たり、土庄側しか行っていないのに島の東側まで行ったように見えた）
REGION_STEMS = {"小豆島"}


def match_by_name(munis, text, prefs, pref_names):
    """本文に出てくる市区町村名（「小樽」「八戸駅」の八戸など）から決める。
    名前を全部書いたもの（土庄町）を、略したもの（小豆島）より先に採り、その中ではいちばん前に出てくるものを採る。
    県と同じ名前の町村（岩手町）は、「岩手」だと県のことなので「岩手町」と書いてあるときだけ当てる。"""
    best = None
    for code, entry in munis.items():
        if prefs and entry["pref"] not in prefs:
            continue
        name = entry["name"]
        stem = SUFFIX.sub("", name)
        words = [(name, True)]
        if (stem not in pref_names or name.endswith("市")) and stem not in REGION_STEMS:
            words.append((stem, False))
        for word, full in words:
            if len(word) < 2:
                continue
            index = text.find(word)
            if index < 0:
                continue
            key = (not full, index, -len(word))
            if best is None or key < best[0]:
                best = (key, code)
    return best[1] if best else None


def places_in(gazetteer, text, prefs, pref_names):
    """本文の名所（南大沢駅・よみうりランド等）を地名辞書で拾い、判定した県の Wikidata ID を返す。
    県の名前（「旅せよ岩手」の岩手）は県のことなので、同じ名前の町村に当てない。"""
    qids = []
    for term, entries in gazetteer.find_in(text):
        if term in pref_names or term in REGION_STEMS:
            continue
        for entry in entries:
            if not prefs or set(entry.get("prefCodes", [])) & prefs:
                qids.append(entry["qid"])
                break
    return qids


def wikidata_coords(qids, cache_path):
    """Wikidata の座標（P625）。公開の地名データなのでリポジトリに控えておき、無い分だけ問い合わせる。"""
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    missing = sorted(q for q in set(qids) if q not in cache)
    for start in range(0, len(missing), 200):
        chunk = missing[start : start + 200]
        query = "SELECT ?item ?coord WHERE { VALUES ?item { %s } ?item wdt:P625 ?coord }" % " ".join(f"wd:{q}" for q in chunk)
        request = urllib.request.Request(
            "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query, "format": "json"}),
            headers={"User-Agent": "portorifo-journey-build/1.0", "Accept": "application/sparql-results+json"},
        )
        rows = json.load(urllib.request.urlopen(request, timeout=60))["results"]["bindings"]
        found = {}
        for row in rows:
            qid = row["item"]["value"].rsplit("/", 1)[-1]
            match = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", row["coord"]["value"])
            if match and qid not in found:
                found[qid] = [float(match.group(2)), float(match.group(1))]  # [緯度, 経度]
        for qid in chunk:
            cache[qid] = found.get(qid)
        time.sleep(1)
    cache_path.write_text(
        json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path, help="N03 の市区町村 GeoJSON")
    parser.add_argument("--report", action="store_true", help="決まらなかった投稿を表示する")
    args = parser.parse_args()

    munis = read_municipalities(args.source)
    print(f"市区町村 {len(munis)}")

    posts = json.loads((JOURNEY / "posts.json").read_text(encoding="utf-8"))["posts"]
    resolved = json.loads((JOURNEY / "resolved.json").read_text(encoding="utf-8"))["posts"]
    gps = json.loads((JOURNEY / "gps.json").read_text(encoding="utf-8"))

    pref_names = {
        p["name"].removesuffix("都").removesuffix("府").removesuffix("県")
        for region in json.loads((JOURNEY / "prefectures.json").read_text(encoding="utf-8"))["regions"]
        for p in region["prefectures"]
    }
    gazetteer = Gazetteer()

    # 座標の無い投稿の名所を先に集め、Wikidata の座標をまとめて引く
    prefs_of = {p["id"]: set(resolved.get(p["id"], {}).get("prefCodes", [])) for p in posts}
    wanted = [q for p in posts if p["id"] not in gps for q in places_in(gazetteer, body_of(p), prefs_of[p["id"]], pref_names)]
    coords = wikidata_coords(wanted, PLACE_COORDS)

    assigned, unresolved = {}, []
    counts = {"gps": 0, "name": 0, "place": 0, "tag": 0}
    for post in posts:
        pid = post["id"]
        prefs = prefs_of[pid]
        code = None
        if pid in gps:
            lat, lon = gps[pid]
            code = locate(munis, lat, lon, prefs)
            method = "gps"
        if not code:
            code, method = match_by_name(munis, body_of(post), prefs, pref_names), "name"
        if not code:
            for qid in places_in(gazetteer, body_of(post), prefs, pref_names):
                if coords.get(qid):
                    code, method = locate(munis, *coords[qid], prefs), "place"
                    if code:
                        break
        if not code:
            code, method = match_by_name(munis, short_tags_of(post), prefs, pref_names), "tag"
        if code:
            assigned[pid] = code
            counts[method] += 1
        else:
            unresolved.append(post)

    print(
        f"座標から {counts['gps']}・地名から {counts['name']}・名所から {counts['place']}・タグから {counts['tag']}"
        f"・決まらない {len(unresolved)} / {len(posts)}"
    )
    if args.report:
        for post in unresolved:
            first = next((l for l in body_of(post).splitlines() if l.strip()), "")
            print(" ", post["id"], sorted(prefs_of[post["id"]]), first[:40])

    OUT_POSTS.write_text(
        json.dumps(
            {
                "_": "投稿ID → 市区町村コード（N03。政令指定都市は市）。座標は公開しないので市区町村に丸めたものだけを置く。build_municipality_maps.py が作る",
                "posts": dict(sorted(assigned.items())),
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    write_maps(munis, assigned)


PREF_OUTLINES = ROOT / "data" / "ontology" / "prefectures.geojson"
AREA_HUBS = JOURNEY / "area_hubs.json"  # エリアの中心を人が決める（「札幌エリア」「新宿エリア」）
AREA_RADIUS = (0.08, 6.0, 40.0)  # エリアの半径：県の長い辺に対する比・下限 km・上限 km（本人「もう少し細かくていい」で 0.12・8〜60 から縮めた）
OWN_AREA_POSTS = 5  # 投稿がこれ以上ある市区町村は、近くの中心にまとめず自分のエリアにする


def write_maps(munis, assigned):
    """訪れた県ごとに、県の形とエリア（近い市区町村をまとめたもの。「札幌エリア」）を書く。
    市区町村ごとだと細かすぎ、六角形のマスだと場所の名前が分からなかった（本人「札幌エリア・府中エリアのように」）"""
    visited = {
        p["code"]
        for region in json.loads((JOURNEY / "prefectures.json").read_text(encoding="utf-8"))["regions"]
        for p in region["prefectures"]
        if p.get("visited")
    }
    outlines = {
        f["properties"]["code"]: f["geometry"]["coordinates"]
        for f in json.loads(PREF_OUTLINES.read_text(encoding="utf-8"))["features"]
    }
    hubs = json.loads(AREA_HUBS.read_text(encoding="utf-8")) if AREA_HUBS.exists() else {}
    counts = {}
    for code in assigned.values():
        counts[code] = counts.get(code, 0) + 1
    maps = {}
    for pref in sorted(visited):
        codes = sorted(c for c, e in munis.items() if e["pref"] == pref)
        if codes and pref in outlines:
            setting = hubs.get(pref, {})
            if isinstance(setting, list):
                setting = {"hubs": setting}
            maps[pref] = pref_map({c: munis[c] for c in codes}, outlines[pref], counts, setting.get("hubs", []), setting.get("radiusKm"))
    OUT_MAPS.write_text(json.dumps(maps, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    size = OUT_MAPS.stat().st_size
    print(f"県の地図 {len(maps)} 県・{size / 1024:.0f}KB")
    for pref in ("01", "13", "37", "14"):
        if pref in maps:
            print(" ", pref, " / ".join(f"{a['label']}({sum(counts.get(c, 0) for c in a['munis'])})" for a in maps[pref]["areas"]))


def ring_centroid(ring):
    """面積で重みを付けた重心。細長い・入り組んだ形でも、だいたい陸の上に来る"""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(a) < 1e-12:
        xs, ys = zip(*ring)
        return sum(xs) / len(xs), sum(ys) / len(ys)
    return cx / (3 * a), cy / (3 * a)


def ring_area(ring):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2


def area_label(name):
    return SUFFIX.sub("", name) + "エリア"


def make_areas(codes, points, munis, counts, manual, radius, project):
    """市区町村をエリアにまとめる。中心は、人が決めたもの（特急の止まる駅の街）・政令指定都市・投稿の多い市区町村。
    ほかの投稿のある市区町村は、半径の中でいちばん近い中心に入る（無ければ自分が新しい中心）。
    投稿の無い市区町村はどのエリアにも入れない（入れると、小豆島の東側のように行っていない所まで塗られた）"""
    shapes = {}

    def dist(code, hub):
        """市区町村の代表点から、中心の市区町村の境界までの距離（中にあれば0）。代表点どうしで測ると、
        札幌のように広い市は重心が山の中に来て、隣の江別が岩見沢エリアに、石狩が美唄エリアに入った"""
        if hub not in shapes:
            rings = [project(polygon[0]) for polygon in munis[hub]["polygons"]]
            shapes[hub] = (rings, bbox_of(rings))
        rings, (x0, y0, x1, y1) = shapes[hub]
        x, y = points[code]
        if not (x0 - radius <= x <= x1 + radius and y0 - radius <= y <= y1 + radius):
            return math.inf
        best = math.inf
        for ring in rings:
            if in_ring(x, y, ring):
                return 0.0
            for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1]):
                dx, dy = bx - ax, by - ay
                t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy or 1e-18)))
                best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
        return best

    by_name = {munis[c]["name"]: c for c in codes}
    hubs = [by_name[name] for name in manual if name in by_name]
    with_posts = sorted((c for c in codes if counts.get(c)), key=lambda c: (not munis[c]["designated"], -counts[c], c))
    # 政令指定都市と投稿の多い市区町村は、近くに中心があっても自分のエリアにする（本人「重要なところは逃さない」。
    # 中心を特急の止まる駅の街にすると、稲城（29件）が府中エリアに、八千代（12件）が船橋エリアに入った）
    hubs += [c for c in with_posts if c not in hubs and (munis[c]["designated"] or counts[c] >= OWN_AREA_POSTS)]
    member_of = {}
    for code in with_posts:
        if code in hubs:
            continue
        near = [(d, h) for d, h in ((dist(code, h), h) for h in hubs) if d <= radius]
        if near:
            member_of[code] = min(near)[1]
        else:
            hubs.append(code)
    areas = {h: [h] for h in hubs}
    for code, hub in member_of.items():
        areas[hub].append(code)
    # 投稿の無いエリア（人が決めた中心に投稿が無いとき）は出さない
    return {h: sorted(m) for h, m in areas.items() if any(counts.get(c) for c in m)}


def pref_map(munis, outline, counts, manual, radius_km=None):
    """県の形（県境）とエリア。本土の塊から遠い島は、投稿のある島だけを差し込み枠に寄せる。
    投稿の位置は市区町村の代表点（いちばん大きい島の重心）で代える。座標は公開しないため"""
    lat0 = sum((e["bbox"][1] + e["bbox"][3]) / 2 for e in munis.values()) / len(munis)
    cos_lat = math.cos(math.radians(lat0))

    def project(ring):
        return [(x * cos_lat, -y) for x, y in ring]

    points = {}
    for code, entry in munis.items():
        biggest = max((polygon[0] for polygon in entry["polygons"]), key=lambda r: ring_area(r))
        points[code] = ring_centroid(project(biggest))

    # 県境の島ごとに分け、いちばん大きい島から近い島を本土にする（近い島から近い島…とはつなげない）
    islands = []
    for polygon in outline:
        rings = [project(r) for r in polygon]
        box = bbox_of(rings[:1])
        islands.append({"rings": rings, "bbox": box, "size": max(box[2] - box[0], box[3] - box[1])})

    def gap(a, b):
        return max(a[0] - b[2], b[0] - a[2], a[1] - b[3], b[1] - a[3], 0)

    def merge(a, b):
        return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))

    largest = max(islands, key=lambda i: i["size"])
    mainland, far_islands, box = [], [], largest["bbox"]
    for island in islands:
        if island is largest or gap(largest["bbox"], island["bbox"]) <= largest["size"] * FAR_RATIO:
            mainland.append(island)
            box = merge(box, island["bbox"])
        else:
            far_islands.append(island)

    def inside(x, y, isles):
        for island in isles:
            x0, y0, x1, y1 = island["bbox"]
            if x0 <= x <= x1 and y0 <= y <= y1 and in_ring(x, y, island["rings"][0]):
                return True
        return False

    span = max(box[2] - box[0], box[3] - box[1])
    mainland = [i for i in mainland if i["size"] >= span * MIN_ISLAND_RATIO / 4]
    width, height = box[2] - box[0], box[3] - box[1]
    scale = VIEW / span
    view_w, view_h = width * scale, height * scale

    def to_view(x, y):
        return ((x - box[0]) * scale, (y - box[1]) * scale)

    def rings_d(isles, transform, extent):
        # 表示では点にしかならない小島は落とす（落とさないと、潰れた小島を原形のまま残す簡略化のせいで 5.6MB になった）
        tolerance = DISPLAY_RATIO * extent
        parts = []
        for island in isles:
            simplified = simplify_polygons({"type": "Polygon", "coordinates": island["rings"]}, tolerance, tolerance * 3)
            for rings in simplified:
                for ring in rings:
                    parts.append("M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in (transform(x, y) for x, y in ring)) + "Z")
        return "".join(parts)

    def muni_d(codes, transform, extent):
        return rings_d(
            [{"rings": [project(r) for r in polygon]} for code in codes for polygon in munis[code]["polygons"]],
            transform,
            extent,
        )

    # エリア。本土と遠い島（差し込み枠）で分けて作る
    on_far = {code for code in munis if inside(*points[code], far_islands)}
    lo, hi = AREA_RADIUS[1], AREA_RADIUS[2]
    # 人が半径を決めた県はそれを使う（東京は県の大きさで決めると約10kmで、府中エリアに調布・稲城まで入った）
    radius = (radius_km or min(max(span * KM_PER_DEGREE * AREA_RADIUS[0], lo), hi)) / KM_PER_DEGREE
    main_codes = sorted(c for c in munis if c not in on_far)
    areas = []
    for hub, members in make_areas(main_codes, points, munis, counts, manual, radius, project).items():
        x, y = to_view(*points[hub])
        areas.append({"label": area_label(munis[hub]["name"]), "munis": members, "d": muni_d(members, to_view, span), "x": round(x, 1), "y": round(y, 1)})

    inset = None
    far = [i for i in far_islands if any(counts.get(code) and inside(*points[code], [i]) for code in munis)]
    if far:
        # 差し込み枠：遠い島をまとめて、本土の右下の外に小さく置く（拡大していることを見出しに書く）
        fbox = bbox_of(r for i in far for r in i["rings"][:1])
        fw, fh = fbox[2] - fbox[0], fbox[3] - fbox[1]
        fscale = VIEW * 0.28 / max(fw, fh, 1e-9)
        ox, oy = view_w + 24, view_h - fh * fscale - 8
        view_w += fw * fscale + 32

        def to_inset(x, y):
            return (ox + (x - fbox[0]) * fscale, oy + (y - fbox[1]) * fscale)

        far_codes = sorted(c for c in on_far if any(inside(*points[c], [i]) for i in far))
        far_areas = make_areas(far_codes, points, munis, counts, manual, radius, project)
        for hub, members in far_areas.items():
            x, y = to_inset(*points[hub])
            # 島の形は市区町村の境界（約50m）から描く。県境（約200m）だと、拡大したときに角ばった多角形になった
            areas.append({"label": area_label(munis[hub]["name"]), "munis": members, "d": muni_d(members, to_inset, max(fw, fh)), "x": round(x, 1), "y": round(y, 1), "inset": True})
        inset = {"box": [round(ox - 6, 1), round(oy - 6, 1), round(fw * fscale + 12, 1), round(fh * fscale + 12, 1)], "label": "（拡大）"}

    return {"viewBox": f"0 0 {view_w:.0f} {view_h:.0f}", "outline": rings_d(mainland, to_view, span), "areas": areas, "inset": inset}


if __name__ == "__main__":
    main()
