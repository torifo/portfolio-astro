#!/usr/bin/env python3
"""旅の背景画像を、本人が置いた元画像からサイト用の webp にする。

  元画像  ~/dev/data/trip-covers/<slug>.<jpg|jpeg|png|heic|webp>（リポジトリの外）
  出力    public/journey/trips/<slug>-800.webp（カード用）・<slug>-1600.webp（見出し・高解像度画面用）
          <slug>-fill.webp（カード・見出しの余白に敷く、端を鏡に映して上下左右へ延ばした画像。CSS でぼかす）
  一覧    data/journey/trip_covers.json（slug → 幅ごとの [幅, 高さ]。サイトの coverFor() が読む）

位置情報などの EXIF は消す（-strip）。縮小だけで拡大はしない。元画像が出力より新しいときだけ作り直す。
元画像を消しても出力は消さない（元画像のフォルダが無い環境で流しても、全部は消えないように）。
trips.json は同期のたびに作り直されて新しい項目が消えるので、一覧は別のファイルにする（slug は一度決まると変わらない）。
元画像のフォルダの README.md に、旅の一覧と届いたかの印を書き出す。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"
SOURCE = ROOT.parents[1] / "data" / "trip-covers"  # ~/dev/data/trip-covers
OUT = ROOT / "public" / "journey" / "trips"
WIDTHS = (800, 1600)
QUALITY = 72
SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
# 余白用の画像は、上下左右それぞれに元の幅・高さの 0.75 倍を鏡に映して延ばす（全体で 2.5 倍）。
# TripCard・trips/[slug] はこの画像を手前の画像の 250% の大きさで中央に重ね、延ばした部分が余白に来るようにする。
# 0.75 あれば、正方形の画像を見出し（横長の帯）に置いたときも余白とぼかしのにじみ（28px）が収まる
FILL_EXTEND = 0.75
FILL_WIDTH = 480
FILL_QUALITY = 55


def magick():
    # Linux の apt で入る ImageMagick 6 には magick が無く convert になる
    return shutil.which("magick") or "convert"


def convert(source, destination, width):
    result = subprocess.run(
        [magick(), str(source), "-auto-orient", "-strip", "-resize", f"{width}x>",
         "-quality", str(QUALITY), f"webp:{destination}"],
        capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(f"変換に失敗した {source.name}: {result.stderr.decode()[:200]}")


def convert_fill(source, destination):
    # 以前は同じ画像を枠いっぱいに拡大してぼかしていたので、手前の画像の端とぼかしの絵柄がずれ、画像が端で切れて見えた。
    # 端を鏡に映して延ばすと、手前の画像の端からそのまま続く絵になる。ぼかすので解像度は低くてよい
    scale = 1 + 2 * FILL_EXTEND
    viewport = (f"%[fx:round(w*{scale})]x%[fx:round(h*{scale})]"
                f"-%[fx:round(w*{FILL_EXTEND})]-%[fx:round(h*{FILL_EXTEND})]")
    result = subprocess.run(
        [magick(), str(source), "-auto-orient", "-strip", "-resize", "640x>",
         "-virtual-pixel", "mirror", "-set", "option:distort:viewport", viewport, "-distort", "SRT", "0", "+repage",
         "-resize", f"{FILL_WIDTH}x", "-quality", str(FILL_QUALITY), f"webp:{destination}"],
        capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(f"余白用の画像の作成に失敗した {source.name}: {result.stderr.decode()[:200]}")


def size_of(path):
    result = subprocess.run(
        [magick(), "identify", "-format", "%w %h", str(path)], capture_output=True, text=True, check=True
    )
    width, height = result.stdout.split()
    return [int(width), int(height)]


def write_readme(source, trips, covers):
    lines = [
        "# 旅の背景画像", "",
        "ファイル名を旅の URL 名にして、このフォルダに置く（jpg・png・heic・webp）。",
        "変換は portfolio-astro で `npm run journey:covers`（位置情報などの EXIF は消える）。", "",
        "| | URL 名（ファイル名） | 期間 | 旅 |", "|---|---|---|---|",
    ]
    for trip in trips:
        period = trip["start"] if trip["start"] == trip["end"] else f"{trip['start']}〜{trip['end'][5:]}"
        lines.append(f"| {'✓' if trip['slug'] in covers else ' '} | {trip['slug']} | {period} | {trip['title']} |")
    (source / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=pathlib.Path, default=SOURCE)
    parser.add_argument("--force", action="store_true", help="新しさに関係なく作り直す")
    args = parser.parse_args()

    if not args.source.is_dir():
        sys.exit(f"元画像のフォルダが無い: {args.source}")
    trips = json.loads((JOURNEY / "trips.json").read_text(encoding="utf-8"))["trips"]
    slugs = {t["slug"] for t in trips}
    manifest_path = JOURNEY / "trip_covers.json"
    covers = json.loads(manifest_path.read_text(encoding="utf-8"))["covers"] if manifest_path.exists() else {}

    sources, unknown = {}, []
    for path in sorted(args.source.iterdir()):
        if path.suffix.lower() not in SUFFIXES:
            continue
        if path.stem not in slugs:
            unknown.append(path.name)
        elif path.stem in sources:
            unknown.append(f"{path.name}（同じ旅の画像が2つある）")
        else:
            sources[path.stem] = path

    OUT.mkdir(parents=True, exist_ok=True)
    made, filled = [], []
    for slug, path in sources.items():
        fill = OUT / f"{slug}-fill.webp"
        if args.force or not fill.exists() or fill.stat().st_mtime < path.stat().st_mtime:
            convert_fill(path, fill)
            filled.append(slug)
        outputs = [OUT / f"{slug}-{width}.webp" for width in WIDTHS]
        fresh = all(o.exists() and o.stat().st_mtime >= path.stat().st_mtime for o in outputs)
        if fresh and slug in covers and not args.force:
            continue
        for width, output in zip(WIDTHS, outputs):
            convert(path, output, width)
        covers[slug] = {str(width): size_of(output) for width, output in zip(WIDTHS, outputs)}
        made.append(slug)

    document = {
        "_": "旅の背景画像の一覧（scripts/journey/build_trip_covers.py が書く）。slug → 幅ごとの [幅, 高さ]。"
             "画像は public/journey/trips/<slug>-<幅>.webp。元画像は ~/dev/data/trip-covers/",
        "covers": dict(sorted(covers.items())),
    }
    manifest_path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_readme(args.source, trips, covers)

    missing = [t for t in trips if t["slug"] not in covers]
    print(f"作り直した {len(made)} 件 / 画像のある旅 {len(covers)} 件 / まだ無い旅 {len(missing)} 件")
    for slug in made:
        print(f"  作成: {slug}  {covers[slug]}")
    if filled:
        print(f"  余白用の画像を作った {len(filled)} 件")
    for name in unknown:
        print(f"  飛ばした（旅に無い名前）: {name}")
    stale = sorted(set(covers) - slugs)
    for slug in stale:
        print(f"  旅に無くなった slug の画像が残っている: {slug}（不要なら public/journey/trips と一覧から手で消す）")


if __name__ == "__main__":
    main()
