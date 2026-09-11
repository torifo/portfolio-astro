#!/usr/bin/env python3
"""投稿の表紙から 480px の webp サムネを作る。

media_url は失効するので画像は自前で持つ。エクスポートは複数の zip に
分割されていて（実測では重複なしの完全な分割）、5GB を展開せずに
zip から直接読んで変換する。

480px は表示サイズから決めている。県ページのグリッドはデスクトップ4列で
カード幅が約232px、モバイル2列で約155px。網膜表示はその2〜3倍を要求するので
どちらも465px前後が必要になる。これ以上小さくすると眠くなる。

品質は70。実測で q80 比 81%（1,013枚で約47.7MB→37MB）に収まり、
空や夕焼けの階調も保つ。q60 まで落とすとバンディングが出はじめる。

出力: public/journey/thumbs/<投稿ID>.webp
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
VIDEO_SUFFIXES = {".mp4", ".mov"}


class MediaStore:
    """分割されたエクスポートをまたいで uri からバイト列を引く。

    zip でも展開済みのフォルダでも同じように読める。分割は重複なしなので、
    先に見つかったほうを使えばよい。
    """

    def __init__(self, sources):
        self.handles = []
        self.index = {}
        self.roots = []
        for path in sources:
            if path.is_dir():
                self.roots.append(path)
                continue
            handle = zipfile.ZipFile(path)
            self.handles.append(handle)
            for name in handle.namelist():
                self.index.setdefault(name, handle)

    def read(self, uri):
        for root in self.roots:
            candidate = root / uri
            if candidate.exists():
                return candidate.read_bytes()
        handle = self.index.get(uri)
        return handle.read(uri) if handle else None


def to_webp(data, destination, size, suffix, quality):
    """ImageMagick に標準入力から渡す。リールは ffmpeg で先頭フレームを抜く。"""
    if suffix in VIDEO_SUFFIXES:
        frame = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", "pipe:0", "-frames:v", "1", "-f", "image2pipe",
             "-vcodec", "png", "pipe:1"],
            input=data,
            capture_output=True,
        )
        if frame.returncode != 0 or not frame.stdout:
            return False, frame.stderr.decode()[:160]
        data = frame.stdout

    result = subprocess.run(
        ["magick", "-", "-auto-orient", "-resize", f"{size}x{size}>", "-quality", str(quality),
         f"webp:{destination}"],
        input=data,
        capture_output=True,
    )
    return result.returncode == 0, result.stderr.decode()[:160]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "sources",
        nargs="+",
        type=pathlib.Path,
        help="エクスポートの zip または展開済みフォルダ（分割分すべて）",
    )
    parser.add_argument("--posts", type=pathlib.Path, default=ROOT / "data" / "journey" / "posts.json")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "public" / "journey" / "thumbs")
    parser.add_argument("--size", type=int, default=480)
    parser.add_argument("--quality", type=int, default=70)
    parser.add_argument("--force", action="store_true", help="既にあるサムネも作り直す")
    args = parser.parse_args()

    posts = json.loads(args.posts.read_text(encoding="utf-8"))["posts"]
    store = MediaStore(args.sources)
    args.out.mkdir(parents=True, exist_ok=True)

    made = skipped = missing = failed = 0
    for index, post in enumerate(posts, 1):
        destination = args.out / f"{post['id']}.webp"
        if destination.exists() and not args.force:
            skipped += 1
            continue
        data = store.read(post["cover"]) if post["cover"] else None
        if data is None:
            missing += 1
            continue
        ok, error = to_webp(
            data, destination, args.size, pathlib.PurePosixPath(post["cover"]).suffix.lower(), args.quality
        )
        if ok:
            made += 1
        else:
            failed += 1
            print(f"  失敗 {post['id']} {post['cover']}: {error}", file=sys.stderr)
        if index % 100 == 0:
            print(f"  {index}/{len(posts)}", flush=True)

    print(f"生成 {made} / 既存 {skipped} / 元が無い {missing} / 失敗 {failed}")
    total = sum(f.stat().st_size for f in args.out.glob("*.webp"))
    print(f"{args.out}: {len(list(args.out.glob('*.webp')))} 枚 {total / 1e6:.1f}MB")


if __name__ == "__main__":
    main()
