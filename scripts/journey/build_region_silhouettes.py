#!/usr/bin/env python3
"""地方ごとのシルエット（SVG パス）を都道府県の境界から作る。

data/ontology/prefectures.geojson の県境を地方ごとにまとめ、平面に投影して
簡略化し、src/lib/region-silhouettes.json に書く。地方グリッドのヘッダーに
透かしとして敷く。

小さな島は落とす（透かしの大きさでは点にしかならず、形が読みにくくなる）。
沖縄は九州から遠く、そのまま入れると九州が小さくなるので、地図の差し込みと
同じ要領で九州の左下に寄せる。
"""
from __future__ import annotations

import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
GEOJSON = ROOT / "data" / "ontology" / "prefectures.geojson"
REGIONS = ROOT / "data" / "journey" / "prefectures.json"
OUT = ROOT / "src" / "lib" / "region-silhouettes.json"

# 形の読みやすさを優先する値。透かしの大きさでは細部は見えない
SIMPLIFY_RATIO = 0.004   # 地方の大きさに対する簡略化の許容幅
MIN_AREA_RATIO = 0.004   # 地方で一番大きい島に対する面積比。これ未満は落とす
MAX_DISTANCE_RATIO = 1.6 # 一番大きい島からの距離（その島の大きさ比）。遠い離島は落とす
INSET_PREF = "47"        # 沖縄
VIEW = 100               # 長辺をこの幅に合わせる


def project(ring, cos_lat):
    return [(lon * cos_lat, -lat) for lon, lat in ring]


def area(ring):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2


def centroid(ring):
    xs, ys = zip(*ring)
    return sum(xs) / len(xs), sum(ys) / len(ys)


def simplify(points, eps):
    """Douglas–Peucker。閉じたリングは始点で2つに割って両側を別々に削る。"""
    if len(points) < 3:
        return points

    def rdp(pts):
        if len(pts) < 3:
            return pts
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        dx, dy = x1 - x0, y1 - y0
        norm = math.hypot(dx, dy) or 1e-12
        far, idx = 0.0, 0
        for i, (x, y) in enumerate(pts[1:-1], start=1):
            d = abs(dy * x - dx * y + x1 * y0 - y1 * x0) / norm
            if d > far:
                far, idx = d, i
        if far <= eps:
            return [pts[0], pts[-1]]
        return rdp(pts[: idx + 1])[:-1] + rdp(pts[idx:])

    half = len(points) // 2
    return rdp(points[: half + 1])[:-1] + rdp(points[half:] + [points[0]])[:-1]


def main():
    geo = {f["properties"]["code"]: f["geometry"] for f in json.loads(GEOJSON.read_text())["features"]}
    regions = json.loads(REGIONS.read_text(encoding="utf-8"))["regions"]

    out = {}
    for region in regions:
        codes = [p["code"] for p in region["prefectures"]]
        lats = [lat for c in codes for poly in geo[c]["coordinates"] for lon, lat in poly[0]]
        cos_lat = math.cos(math.radians(sum(lats) / len(lats)))

        rings = []  # (県コード, 投影済みの外周)
        for code in codes:
            for poly in geo[code]["coordinates"]:
                rings.append((code, project(poly[0], cos_lat)))

        main_rings = [r for r in rings if r[0] != INSET_PREF]
        biggest = max(main_rings, key=lambda r: area(r[1]))[1]
        big_area, (bx, by) = area(biggest), centroid(biggest)
        reach = math.sqrt(big_area) * MAX_DISTANCE_RATIO

        kept, inset = [], []
        for code, ring in rings:
            if area(ring) < big_area * MIN_AREA_RATIO:
                continue
            if code == INSET_PREF:
                inset.append(ring)
                continue
            cx, cy = centroid(ring)
            if math.hypot(cx - bx, cy - by) > reach:
                continue
            kept.append(ring)

        # 沖縄は本島だけを九州の左下の海へ寄せる（県全体だと先島まで入って横に長くなる）
        if inset:
            island = max(inset, key=area)
            xs = [x for r in kept for x, _ in r]
            ys = [y for r in kept for _, y in r]
            ixs = [x for x, _ in island]
            iys = [y for _, y in island]
            gap = (max(ys) - min(ys)) * 0.04
            dx = (min(xs) - gap) - max(ixs)
            dy = max(ys) - max(iys)
            kept.append([(x + dx, y + dy) for x, y in island])

        xs = [x for r in kept for x, _ in r]
        ys = [y for r in kept for _, y in r]
        minx, miny = min(xs), min(ys)
        span = max(max(xs) - minx, max(ys) - miny)
        scale = VIEW / span
        eps = span * SIMPLIFY_RATIO

        parts = []
        for ring in kept:
            pts = simplify(ring, eps)
            if len(pts) < 3:
                continue
            coords = [f"{(x - minx) * scale:.1f} {(y - miny) * scale:.1f}" for x, y in pts]
            parts.append("M" + "L".join(coords) + "Z")
        width = round((max(xs) - minx) * scale, 1)
        height = round((max(ys) - miny) * scale, 1)
        out[region["name"]] = {"viewBox": f"0 0 {width} {height}", "d": "".join(parts)}
        print(f"  {region['name']:<6} 島 {len(parts):>2} / パス {len(out[region['name']]['d']):>5} 文字 / {width}x{height}")

    OUT.write_text(json.dumps(out, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{OUT} に {len(out)} 地方")


if __name__ == "__main__":
    main()
