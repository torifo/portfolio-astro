#!/usr/bin/env python3
"""聖地巡礼の作品の背景画像を、元画像からサイト用の webp にする（旅の画像と同じ作り）。

  元画像  ~/dev/data/work-covers/<slug>.<jpg|jpeg|png|heic|webp>（リポジトリの外）
  出典    ~/dev/data/work-covers/meta.json  {"<slug>": {"credit": "写真：… / CC BY-SA 4.0", "mode": "cover", "focus": "50% 30%", "source": "URL"}}
          本人の画像は credit を書かない。mode は一覧の帯での置き方（cover＝帯いっぱいに切り取る／fit＝全体を見せて余白をぼかす。
          無ければ形で決める）、focus は切り取るときの中心（無ければ中央）
  出力    public/journey/works/<slug>-800.webp・<slug>-1600.webp・<slug>-fill.webp
  一覧    data/journey/work_covers.json（slug → 幅ごとの [幅, 高さ]・credit・focus。サイトの workCoverFor() が読む）

変換の中身（EXIF を消す・縮小だけ・余白用に端を鏡に映して延ばす）は build_trip_covers.py と同じ。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_trip_covers import SUFFIXES, WIDTHS, convert, convert_fill, size_of  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "data" / "journey"
SOURCE = ROOT.parents[1] / "data" / "work-covers"  # ~/dev/data/work-covers
OUT = ROOT / "public" / "journey" / "works"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=pathlib.Path, default=SOURCE)
    parser.add_argument("--force", action="store_true", help="新しさに関係なく作り直す")
    args = parser.parse_args()

    if not args.source.is_dir():
        sys.exit(f"元画像のフォルダが無い: {args.source}")
    works = json.loads((JOURNEY / "pilgrimages.json").read_text(encoding="utf-8"))["works"]
    slugs = {w["slug"] for w in works if not w.get("untitled")}
    meta_path = args.source / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    manifest_path = JOURNEY / "work_covers.json"
    covers = json.loads(manifest_path.read_text(encoding="utf-8"))["covers"] if manifest_path.exists() else {}

    sources, skipped = {}, []
    for path in sorted(args.source.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        if path.stem not in slugs:
            skipped.append(path.name)
        elif path.stem in sources:
            skipped.append(f"{path.name}（同じ作品の画像が2つある）")
        else:
            sources[path.stem] = path

    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for slug, path in sources.items():
        outputs = [OUT / f"{slug}-{width}.webp" for width in WIDTHS]
        fill = OUT / f"{slug}-fill.webp"
        fresh = all(o.exists() and o.stat().st_mtime >= path.stat().st_mtime for o in [*outputs, fill])
        if args.force or not fresh or slug not in covers:
            convert_fill(path, fill)
            for width, output in zip(WIDTHS, outputs):
                convert(path, output, width)
            made.append(slug)
        entry = {str(width): size_of(output) for width, output in zip(WIDTHS, outputs)}
        # 出典と切り取りの中心は meta.json が正。書いていなければ載せない（本人の画像）
        for key in ("credit", "source", "mode", "focus"):
            if meta.get(slug, {}).get(key):
                entry[key] = meta[slug][key]
        covers[slug] = entry

    document = {
        "_": "聖地巡礼の作品の背景画像の一覧（scripts/journey/build_work_covers.py が書く）。slug → 幅ごとの [幅, 高さ]・"
             "credit（画像の出典の表示）・source（出典のページ）・mode（帯での置き方）・focus（帯で切り取るときの中心）。画像は public/journey/works/<slug>-<幅>.webp。"
             "元画像は ~/dev/data/work-covers/",
        "covers": dict(sorted(covers.items())),
    }
    manifest_path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"作り直した {len(made)} 件 / 画像のある作品 {len(covers)} 件 / まだ無い作品 {len(slugs - set(covers))} 件")
    for slug in made:
        print(f"  作成: {slug}  {covers[slug]}")
    for name in skipped:
        print(f"  飛ばした（作品に無い名前）: {name}")


if __name__ == "__main__":
    main()
