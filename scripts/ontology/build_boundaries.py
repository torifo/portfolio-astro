#!/usr/bin/env python3
"""都道府県の境界ポリゴンを、座標から県を引ける最小限の形に落とす。

GPS から県を決めるためだけに使うので、表示用の精度は要らない。ただし
海岸や島で撮った写真が県の外へ落ちると判定できなくなるため、簡略化は
控えめにし、外れた点は最近傍の県へ寄せる（scripts/journey/geo.py）。

入力は2種類を受ける。出力の形は同じなので、下流（scripts/journey/geo.py）は
どちらで作ったかを知らなくてよい。

  * dataofjapan/land の japan.geojson … 47フィーチャ・既にある程度簡略化済み
  * 国土数値情報 N03 の _prefecture.geojson … 1ポリゴン1フィーチャ・520MB・全精度

N03 は 1行1フィーチャで書かれているので、行ごとに読んで簡略化し、捨てながら進む。
520MB を丸ごとメモリに載せる必要はない。
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]


def perpendicular_distance(point, start, end):
    (px, py), (sx, sy), (ex, ey) = point, start, end
    dx, dy = ex - sx, ey - sy
    if dx == 0 and dy == 0:
        return math.hypot(px - sx, py - sy)
    t = ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (sx + t * dx), py - (sy + t * dy))


def thin(points, tolerance):
    """Douglas-Peucker の前処理。許容距離より近い連続点を落とす。

    N03 の海岸線は小数15桁で数百万点ある。DP は点数に対して重いので、
    先に O(n) で間引いておかないと現実的な時間で終わらない。
    """
    if len(points) < 3:
        return list(points)
    kept = [points[0]]
    for point in points[1:-1]:
        last = kept[-1]
        if abs(point[0] - last[0]) > tolerance or abs(point[1] - last[1]) > tolerance:
            kept.append(point)
    kept.append(points[-1])
    return kept


def simplify(points, tolerance):
    """Douglas-Peucker。再帰ではなくスタックで回す（日本の海岸線は点が多い）。"""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        worst, worst_index = 0.0, -1
        for i in range(first + 1, last):
            d = perpendicular_distance(points[i], points[first], points[last])
            if d > worst:
                worst, worst_index = d, i
        if worst > tolerance:
            keep[worst_index] = True
            stack.append((first, worst_index))
            stack.append((worst_index, last))
    return [p for p, k in zip(points, keep) if k]


def simplify_ring(ring, tolerance):
    points = [tuple(p) for p in ring]
    candidate = thin(points, tolerance / 2) if tolerance > 0 else points
    simplified = simplify(candidate, tolerance)
    if len(simplified) < 4:
        # 簡略化で潰れた小島は原形のまま残す。与論島のような離島は
        # 投稿が集中する場所なので、ここで落とすと県が引けなくなる。
        simplified = points
    if len(simplified) < 4:
        return None
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    return [[round(x, 5), round(y, 5)] for x, y in simplified]


def ring_extent(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def simplify_polygons(geometry, tolerance, min_extent=0.0):
    """MultiPolygon / Polygon を輪ごとに簡略化して、ポリゴンの一覧で返す。

    min_extent より小さい島は捨てる。N03 は岩礁ひとつまで含むので、そのまま
    使うと12万ポリゴンになる。捨てた島の上で撮った写真は geo.py の最近傍で
    拾われ、たいてい同じ県に落ちる。
    """
    if geometry["type"] == "Polygon":
        raw = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        raw = geometry["coordinates"]
    else:
        raise ValueError(f"想定外のジオメトリ: {geometry['type']}")

    out = []
    for polygon in raw:
        if min_extent and ring_extent(polygon[0]) < min_extent:
            continue
        rings = []
        for index, ring in enumerate(polygon):
            simplified = simplify_ring(ring, tolerance)
            if simplified is None:
                if index == 0:
                    break  # 外周が消えたらこのポリゴンごと捨てる
                continue
            rings.append(simplified)
        if rings:
            out.append(rings)
    return out


FEATURE_LINE = re.compile(rb'^\s*(\{\s*"type":\s*"Feature".*?\})\s*,?\s*$')


def read_features(path):
    """(県コード, ジオメトリ) を順に返す。N03 は行ごとに読み、捨てながら進む。"""
    with path.open("rb") as handle:
        head = handle.read(400)
    if b'"N03_' in head or b"N03-" in head:
        with path.open("rb") as handle:
            for line in handle:
                match = FEATURE_LINE.match(line)
                if not match:
                    continue
                feature = json.loads(match.group(1))
                # N03_007 は全国地方公共団体コード。頭2桁が都道府県。
                code = str(feature["properties"].get("N03_007") or "")[:2]
                if len(code) == 2:
                    yield code, feature["geometry"]
        return

    source = json.loads(path.read_text(encoding="utf-8"))
    for feature in source["features"]:
        yield f"{int(feature['properties']['id']):02d}", feature["geometry"]


def count_points(polygons):
    return sum(len(ring) for polygon in polygons for ring in polygon)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path, help="入力 GeoJSON")
    parser.add_argument(
        "-o", "--out", type=pathlib.Path, default=ROOT / "data" / "ontology" / "prefectures.geojson"
    )
    parser.add_argument(
        "-m",
        "--min-extent",
        type=float,
        default=0.0,
        help="この差し渡し（度）より小さい島を捨てる。0.005 で約600m",
    )
    parser.add_argument(
        "-t",
        "--tolerance",
        type=float,
        default=0.002,
        help="Douglas-Peucker の許容距離（度）。0.002 で約 200m",
    )
    args = parser.parse_args()

    names = {
        p["code"]: p["name"]
        for p in json.loads((ROOT / "data" / "ontology" / "prefectures.json").read_text(encoding="utf-8"))
    }

    by_code, before, after = {}, 0, 0
    for code, geometry in read_features(args.source):
        before += count_points(simplify_polygons(geometry, 0.0))
        polygons = simplify_polygons(geometry, args.tolerance, args.min_extent)
        after += count_points(polygons)
        by_code.setdefault(code, []).extend(polygons)

    features = [
        {
            "type": "Feature",
            "properties": {"code": code, "name": names.get(code, code)},
            "geometry": {"type": "MultiPolygon", "coordinates": polygons},
        }
        for code, polygons in sorted(by_code.items())
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    size = args.out.stat().st_size
    print(f"{args.out}  {size / 1e6:.1f}MB")
    print(f"  頂点 {before:,} -> {after:,} ({after / before:.1%})  許容距離 {args.tolerance}度")
    print(f"  都道府県 {len(features)} / ポリゴン {sum(len(f['geometry']['coordinates']) for f in features):,}")


if __name__ == "__main__":
    main()
