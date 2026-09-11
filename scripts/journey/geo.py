#!/usr/bin/env python3
"""緯度経度 -> 都道府県。県境ポリゴンだけを使い、外部サービスは呼ばない。

海岸・港・船上・展望台からの撮影では、簡略化した県境の外側に点が落ちる。
そのため内外判定で決まらなかった点は最近傍の県へ寄せ、どれだけ離れていたかを
一緒に返す。距離が大きい点は判定を捨てられるようにしておく。
"""
from __future__ import annotations

import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
BOUNDARIES = ROOT / "data" / "ontology" / "prefectures.geojson"

# 緯度1度あたりの距離。経度は緯度に応じて縮む。
KM_PER_DEGREE = 111.32

# 県境の外に落ちた点を寄せる上限。これより遠ければ判定しない。
NEAREST_LIMIT_KM = 15.0


def _bbox(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _in_ring(lon, lat, ring):
    """Ray casting。境界上の点の扱いは問わない（県境ちょうどの投稿は無い）。"""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            if lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def _segment_distance_km(lon, lat, ring, scale):
    """点から輪までの最短距離。緯度に応じて経度方向を縮めた平面で測る。"""
    best = float("inf")
    px, py = lon * scale, lat
    j = len(ring) - 1
    for i in range(len(ring)):
        ax, ay = ring[i][0] * scale, ring[i][1]
        bx, by = ring[j][0] * scale, ring[j][1]
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            d = math.hypot(px - ax, py - ay)
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
            d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
        best = min(best, d)
        j = i
    return best * KM_PER_DEGREE


class Boundaries:
    def __init__(self, path=BOUNDARIES):
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        self.entries = []
        for feature in data["features"]:
            code = feature["properties"]["code"]
            for polygon in feature["geometry"]["coordinates"]:
                outer = polygon[0]
                self.entries.append((code, _bbox(outer), outer, polygon[1:]))

    def locate(self, lat, lon):
        """(県コード, 距離km) を返す。距離0は内側。決まらなければ (None, None)。"""
        for code, (minx, miny, maxx, maxy), outer, holes in self.entries:
            if not (minx <= lon <= maxx and miny <= lat <= maxy):
                continue
            if _in_ring(lon, lat, outer) and not any(_in_ring(lon, lat, h) for h in holes):
                return code, 0.0

        # どの県にも入らなかった。海上・埋立地・簡略化の誤差のいずれか。
        scale = math.cos(math.radians(lat))
        best_code, best_km = None, float("inf")
        for code, (minx, miny, maxx, maxy), outer, _ in self.entries:
            # 外接矩形までの距離が既に上回るポリゴンは測らない
            dx = max(minx - lon, 0, lon - maxx) * scale
            dy = max(miny - lat, 0, lat - maxy)
            if math.hypot(dx, dy) * KM_PER_DEGREE >= best_km:
                continue
            km = _segment_distance_km(lon, lat, outer, scale)
            if km < best_km:
                best_code, best_km = code, km

        if best_code and best_km <= NEAREST_LIMIT_KM:
            return best_code, round(best_km, 2)
        return None, round(best_km, 2) if best_code else None
