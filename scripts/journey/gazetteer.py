#!/usr/bin/env python3
"""タグ・キャプションから都道府県を引くための索引。

data/ontology/places.json（機械生成・98,320件）は「候補源」であって確定辞書ではない。
Wikidata 由来の誤りが実際に混ざっている（利根川が長野県の市区町村に紐付く等）ため、
最終的な正は data/journey/gazetteer.json（人が育てる確定辞書）と
data/journey/overrides.json（人の手動指定）にある。
"""
from __future__ import annotations

import gzip
import json
import pathlib
import re
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[2]
ONTOLOGY = ROOT / "data" / "ontology"
JOURNEY = ROOT / "data" / "journey"

# 「横須賀市」→「横須賀」のように、本人がタグで使う短い呼び方を作るための接尾辞。
# 郡は「◯◯郡」単体で使われることがないので落とさない。
MUNICIPAL_SUFFIX = re.compile(r"(市|区|町|村)$")

# 索引に載せると誤爆するだけの語。実データのタグ頻度上位から拾った一般名詞。
STOPWORDS = {
    "散策", "散歩", "自然", "ドライブ", "公園", "橋", "旅", "旅行", "観光", "風景",
    "写真", "景色", "神社", "寺", "城", "駅", "山", "海", "川", "湖", "滝", "温泉",
    "花", "桜", "紅葉", "雪", "夜景", "電車", "新幹線", "バス", "飛行機", "船",
}

# 部分一致で拾う最短の長さ。これ未満だと「旅」「山」のような語で誤爆する。
MIN_SUBSTRING = 3

# ただし「箱根」「日光」のような2文字の地名は落としたくない。市区町村か、
# 十分に有名（サイトリンクが多い）な地名であれば2文字でも部分一致に載せる。
SHORT_SUBSTRING = 2
SHORT_SITELINKS = 10


def normalize(text: str) -> str:
    """全角英数・互換文字を寄せ、ラテン文字は小文字に畳む。"""
    return unicodedata.normalize("NFKC", text).strip().casefold()


def _load_places():
    """places.json は 11.7MB あるので gzip で同梱している。

    build_places.py が吐いた生の places.json があればそちらを優先する
    （再生成した直後に圧縮し直さなくても動くように）。
    """
    raw = ONTOLOGY / "places.json"
    if raw.exists():
        return json.loads(raw.read_text(encoding="utf-8"))
    with gzip.open(ONTOLOGY / "places.json.gz", "rt", encoding="utf-8") as handle:
        return json.load(handle)


class Gazetteer:
    def __init__(self):
        self.prefectures = json.loads((ONTOLOGY / "prefectures.json").read_text(encoding="utf-8"))
        self.municipalities = json.loads((ONTOLOGY / "municipalities.json").read_text(encoding="utf-8"))
        self.places = _load_places()

        self.pref_name = {p["code"]: p["name"] for p in self.prefectures}

        # 県名そのもの（L2）。「秋田県」「秋田」の双方を引けるようにする。
        self.pref_terms: dict[str, list[str]] = {}
        for pref in self.prefectures:
            code, name = pref["code"], pref["name"]
            self._add(self.pref_terms, name, code)
            bare = re.sub(r"(都|道|府|県)$", "", name)
            if bare != name:
                self._add(self.pref_terms, bare, code)

        # 地名の索引（L4）。term -> 候補エントリの一覧。
        self.terms: dict[str, list[dict]] = {}
        for place in self.places:
            for term in [place["name"], *place.get("aliases", [])]:
                self._add_place(term, place)

        # 全国地方公共団体コードを持つ市区町村は公式の識別子に裏打ちされているので、
        # 同名の集落より優先する。「横須賀」が静岡の集落に負けるのを防ぐ。
        self.municipal_qids = {m["qid"] for m in self.municipalities}
        by_qid = {p["qid"]: p for p in self.places}

        # 改善1: 市区町村の接尾辞を落とした呼び方を足す。
        # 「府中」のように複数県で衝突する語はそのまま複数候補として残す
        # （県で割れるので曖昧と判定され、勝手に片方へ倒れない）。
        for muni in self.municipalities:
            short = MUNICIPAL_SUFFIX.sub("", muni["name"])
            if not short or short == muni["name"]:
                continue
            entry = by_qid.get(muni["qid"]) or {
                "qid": muni["qid"],
                "name": muni["name"],
                "prefCodes": [muni["prefCode"]],
                "kinds": ["市区町村"],
                "sitelinks": 0,
            }
            self._add_place(short, entry)

        # 人が育てる確定辞書と手動指定。無くても動く。
        self.curated = self._load_map(JOURNEY / "gazetteer.json")
        self.overrides = self._load_map(JOURNEY / "overrides.json")

        # 部分一致用の語を長さ降順で持つ（最長一致を優先するため）。
        self.substring_terms = sorted(
            (t for t in self.terms if self._substring_ok(t)),
            key=len,
            reverse=True,
        )

    def _substring_ok(self, term: str) -> bool:
        if len(term) >= MIN_SUBSTRING:
            return True
        if len(term) < SHORT_SUBSTRING:
            return False
        # 2文字は裏付けのある地名だけ通す
        return any(
            e["qid"] in self.municipal_qids or e.get("sitelinks", 0) >= SHORT_SITELINKS
            for e in self.terms[term]
        )

    @staticmethod
    def _load_map(path: pathlib.Path) -> dict[str, list[str]]:
        if not path.exists():
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {normalize(k): v for k, v in raw.items()}

    @staticmethod
    def _add(target: dict, term: str, value):
        key = normalize(term)
        if key:
            target.setdefault(key, []).append(value)

    def _add_place(self, term: str, place: dict):
        key = normalize(term)
        if not key or key in STOPWORDS or term in STOPWORDS:
            return
        bucket = self.terms.setdefault(key, [])
        if not any(e["qid"] == place["qid"] for e in bucket):
            bucket.append(place)

    def lookup(self, term: str) -> list[dict]:
        return self.terms.get(normalize(term), [])

    def prioritize(self, entries: list[dict]) -> list[dict]:
        """市区町村の候補があればそれだけに絞る。無ければそのまま返す。"""
        municipal = [e for e in entries if e["qid"] in self.municipal_qids]
        return municipal or entries

    def find_in(self, text: str) -> list[tuple[str, list[dict]]]:
        """テキスト内に含まれる地名を最長一致で拾う（改善2: 旅タグ内の部分一致）。"""
        haystack = normalize(text)
        hits, consumed = [], []
        for term in self.substring_terms:
            start = haystack.find(term)
            if start < 0:
                continue
            end = start + len(term)
            if any(s < end and start < e for s, e in consumed):
                continue  # すでに拾った語の内側なので飛ばす
            consumed.append((start, end))
            hits.append((term, self.terms[term]))
        return hits
