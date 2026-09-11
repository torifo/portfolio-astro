#!/usr/bin/env python3
"""Instagram データエクスポート（JSON形式）を Journey 用の正規化レコードへ変換する。

入力: <export>/your_instagram_activity/media/{posts.json,reels.json}
出力: data/journey/posts.json

エクスポート固有の罠をここで吸収する。下流はこのファイルだけを読む。

  * 文字化け  … Instagram は UTF-8 のバイト列を latin-1 として書き出す
  * 不可視文字 … キャプションに U+2061 等が散在し、除去しないとタグが切れる
  * 日付      … timestamp は「アップロード日時」であって撮影日ではない。
                後追い投稿のときだけ本人がキャプション先頭に日付を書いているので、
                キャプションに日付があればそれを、無ければ当日投稿なので
                アップロード日時を採用する。
  * カルーセル … 2枚目以降は label_values の入れ子 dict に入る。GPS を持つのは
                表紙のみで、1投稿あたり最大1点（実測）。

タグは解決できたものだけでなく全件を原文のまま保存する。聖地巡礼など別軸の
ページが後から生えるため、ここで捨てると取り込みからやり直しになる。

**緯度経度は posts.json に入れず gps.json へ分ける。** リポジトリが公開なので、
943件ぶんの小数6桁の座標をそのまま入れると生活圏が特定できてしまう
（実測で、同じ1km圏に6年分・22件の出入りが残っていた）。サイトは座標を
表示せず県コードしか使わないため、公開側から外しても何も落ちない。
gps.json は .git/info/exclude で除外する。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

JST = dt.timezone(dt.timedelta(hours=9))

# キャプションに紛れ込む不可視文字。U+2061 (FUNCTION APPLICATION) が大半。
INVISIBLE = re.compile(r"[⁠-⁤​-‏﻿]")

# 「#タグ」。区切りは半角2スペース・全角スペース・改行のいずれか。
HASHTAG = re.compile(r"#([^\s　#]+)")

# キャプション先頭の撮影日。本人の書き方は主に次の4通り（実データで確認）。
#   2025-06-17 / 2025.6.17 / 2025/6/17   … 416件
#   2025年6月17日                         … 461件
#   2025年6月                             …  32件（日が無い）
#   2025-06                               …（日が無い）
# 日まで無いものは月の1日に寄せ、precision を month として残す。
LEADING_DATE = re.compile(
    r"^\s*(20\d{2})\s*(?:[-/.]|年)\s*(\d{1,2})\s*(?:(?:[-/.]|月)\s*(\d{1,2})\s*日?)?"
)


def demojibake(value):
    """latin-1 として書き出された UTF-8 を復元する。"""
    if isinstance(value, str):
        try:
            return value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    if isinstance(value, list):
        return [demojibake(v) for v in value]
    if isinstance(value, dict):
        return {demojibake(k): demojibake(v) for k, v in value.items()}
    return value


def label(label_values, name):
    for entry in label_values:
        if entry.get("label") == name:
            return entry
    return None


def label_value(label_values, name):
    entry = label(label_values, name)
    return (entry or {}).get("value") or ""


def collect_media(node, found):
    """入れ子のどこにあってもメディアを順序どおり拾う（カルーセル対応）。"""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "media" and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "uri" in item:
                        found.append(item)
            else:
                collect_media(value, found)
    elif isinstance(node, list):
        for item in node:
            collect_media(item, found)


def exif_gps(media_item):
    metadata = media_item.get("media_metadata") or {}
    for key in ("photo_metadata", "video_metadata"):
        for entry in (metadata.get(key) or {}).get("exif_data") or []:
            lat, lon = entry.get("latitude"), entry.get("longitude")
            if lat is None or (lat == 0 and lon == 0):
                continue  # 0,0 は位置情報なしの意味。ナル島で撮った写真は無い
            return [round(float(lat), 6), round(float(lon), 6)]
    return None


def clean_caption(raw):
    return INVISIBLE.sub("", raw or "").strip()


def resolve_date(caption, uploaded):
    """撮影日・精度・その根拠を返す。

    アップロード日時は撮影日ではない。本人が後から投稿したときだけ
    キャプション先頭に日付を書いているので、日付が無ければ当日投稿とみなす。
    """
    match = LEADING_DATE.match(caption)
    if match:
        year, month, day = match.group(1), match.group(2), match.group(3)
        try:
            if day:
                return dt.date(int(year), int(month), int(day)).isoformat(), "day", "caption"
            return dt.date(int(year), int(month), 1).isoformat(), "month", "caption"
        except ValueError:
            pass  # 2025-13-45 のような書き間違いは当日投稿として扱う
    return uploaded.date().isoformat(), "day", "upload"


def build_record(post_id, kind, caption, uploaded, media_items, post_level_gps=None):
    caption = clean_caption(caption)
    date, date_precision, date_source = resolve_date(caption, uploaded)

    uris, seen = [], set()
    gps = None
    for item in media_items:
        uri = item.get("uri")
        if uri and uri not in seen:
            seen.add(uri)
            uris.append(uri)
        if gps is None:
            gps = exif_gps(item)
    if gps is None:
        gps = post_level_gps

    return {
        "id": post_id,
        "kind": kind,
        "date": date,
        "date_precision": date_precision,
        "date_source": date_source,
        "uploaded_at": uploaded.isoformat(),
        "caption": caption,
        "hashtags": HASHTAG.findall(caption),
        "cover": uris[0] if uris else None,
        "media": uris,
        # 座標はここには入れない。呼び出し側が gps.json へ振り分ける。
        "_gps": gps,
    }


def parse_posts(path):
    records = []
    for post in demojibake(json.loads(path.read_text(encoding="utf-8"))):
        label_values = post.get("label_values", [])
        uploaded = dt.datetime.fromtimestamp(post["timestamp"], JST)

        media_items = []
        collect_media(post, media_items)

        # 表紙の EXIF が落ちていても投稿レベルの緯度経度ラベルが残ることがある。
        # GPS が無い投稿では両方とも "0" になる（実測・63件すべて）。
        lat = label_value(label_values, "緯度")
        lon = label_value(label_values, "経度")
        post_gps = None
        if lat not in ("", "0", "0.0") and lon not in ("", "0", "0.0"):
            post_gps = [round(float(lat), 6), round(float(lon), 6)]

        records.append(
            build_record(
                post_id=str(post.get("fbid") or ""),
                kind="post",
                caption=label_value(label_values, "キャプション"),
                uploaded=uploaded,
                media_items=media_items,
                post_level_gps=post_gps,
            )
        )
    return records


def parse_reels(path):
    records = []
    for reel in demojibake(json.loads(path.read_text(encoding="utf-8"))).get("ig_reels_media", []):
        media_items = []
        collect_media(reel, media_items)
        if not media_items:
            continue
        head = media_items[0]
        uploaded = dt.datetime.fromtimestamp(head.get("creation_timestamp", 0), JST)
        # リールは fbid を持たないのでメディアのファイル名を ID にする。
        reel_id = pathlib.PurePosixPath(head["uri"]).stem
        records.append(
            build_record(
                post_id=reel_id,
                kind="reel",
                caption=head.get("title", ""),
                uploaded=uploaded,
                media_items=media_items,
            )
        )
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "export",
        type=pathlib.Path,
        help="エクスポートの展開先（your_instagram_activity/ を含むディレクトリ）",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[2] / "data" / "journey" / "posts.json",
    )
    args = parser.parse_args()

    media_dir = args.export / "your_instagram_activity" / "media"
    posts_path = media_dir / "posts.json"
    if not posts_path.exists():
        sys.exit(f"posts.json が見つからない: {posts_path}")

    records = parse_posts(posts_path)
    reels_path = media_dir / "reels.json"
    if reels_path.exists():
        records += parse_reels(reels_path)

    # 撮影日の新しい順。同日内はアップロード順を保つ。
    records.sort(key=lambda r: (r["date"], r["uploaded_at"]), reverse=True)

    # 座標を切り離す。posts.json は公開、gps.json は手元だけ。
    coordinates = {r["id"]: r.pop("_gps") for r in records}
    coordinates = {k: v for k, v in coordinates.items() if v}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "generated_at": dt.datetime.now(JST).isoformat(timespec="seconds"),
                "source": args.export.name,
                "posts": records,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    gps_path = args.out.with_name("gps.json")
    gps_path.write_text(
        json.dumps(
            {
                "_": "投稿ID -> [緯度, 経度]。撮影地そのものなので公開しない"
                "（.git/info/exclude で除外）。県の判定にだけ使い、サイトには出さない。",
                **coordinates,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    dated = sum(1 for r in records if r["date_source"] == "caption")
    monthly = sum(1 for r in records if r["date_precision"] == "month")
    tagged = sum(1 for r in records if r["hashtags"])
    located = len(coordinates)
    total = len(records)
    print(f"{args.out} に {total} 件")
    print(f"  キャプション日付 {dated} (うち月まで {monthly}) / 当日投稿 {total - dated}")
    print(f"  タグあり {tagged} ({tagged / total:.1%})")
    print(f"  GPS あり {located} ({located / total:.1%}) -> {gps_path}（非公開）")


if __name__ == "__main__":
    main()
