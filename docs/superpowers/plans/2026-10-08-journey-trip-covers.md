# 旅の背景画像 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 旅ごとに本人が用意した画像を、旅の一覧のカード・旅のページの見出し・県のページの旅カードの背景に敷く（無ければ投稿のサムネ）。

**Architecture:** 元画像は `~/dev/data/trip-covers/<slug>.<拡張子>`（リポジトリの外）。`scripts/journey/build_trip_covers.py` が EXIF を消した webp（800w・1600w）を `public/journey/trips/` に作り、`data/journey/trip_covers.json` に一覧を書く。サイトは `coverFor(trip)` でその一覧を引き、`TripCard.astro` と旅のページの見出しで背景に敷く。

**Tech Stack:** Python 3 + ImageMagick（`build_thumbs.py` と同じ）、Astro 5 + Tailwind 4。テストの仕組みはリポジトリに無いので、各タスクはコマンドの出力とビルド結果で確かめる。

設計: `docs/superpowers/specs/2026-10-08-journey-trip-covers-design.md`

---

### Task 1: 変換スクリプトと一覧

**Files:**
- Create: `scripts/journey/build_trip_covers.py`
- Modify: `package.json`（scripts に `journey:covers`）
- Create（生成）: `data/journey/trip_covers.json`、`public/journey/trips/*.webp`、`~/dev/data/trip-covers/README.md`

- [ ] **Step 1: スクリプトを書く**

```python
#!/usr/bin/env python3
"""旅の背景画像を、本人が置いた元画像からサイト用の webp にする。

  元画像  ~/dev/data/trip-covers/<slug>.<jpg|jpeg|png|heic|webp>（リポジトリの外）
  出力    public/journey/trips/<slug>-800.webp（カード用）・<slug>-1600.webp（見出し・高解像度画面用）
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
    made = []
    for slug, path in sources.items():
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
    for name in unknown:
        print(f"  飛ばした（旅に無い名前）: {name}")
    stale = sorted(set(covers) - slugs)
    for slug in stale:
        print(f"  旅に無くなった slug の画像が残っている: {slug}（不要なら public/journey/trips と一覧から手で消す）")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: npm スクリプトを足す**

`package.json` の `"journey:refresh"` の次の行に:

```json
    "journey:covers": "python3 scripts/journey/build_trip_covers.py",
```

- [ ] **Step 3: 流して確かめる**

Run: `npm run journey:covers`
Expected: `作り直した 8 件 / 画像のある旅 8 件 / まだ無い旅 24 件`、`public/journey/trips/` に16ファイル

Run: `npm run journey:covers`（2回目）
Expected: `作り直した 0 件`、`git status` で一覧が変わらない

Run: `for f in public/journey/trips/*.webp; do magick identify -verbose "$f" | grep -ci 'exif:' ; done | sort -u`
Expected: `0` だけ（EXIF が残っていない）

- [ ] **Step 4: Commit**

```bash
git add scripts/journey/build_trip_covers.py package.json data/journey/trip_covers.json public/journey/trips
git commit  # 英語 subject + 空行 + --- + 日本語本文。Claude の署名は入れない
```

### Task 2: `coverFor()` と写真の上の文字

**Files:**
- Modify: `src/lib/journey.ts`（import と、`thumbUrl` の後に `coverFor`）
- Modify: `src/styles/global.css`（末尾に `.photo-title`・`.photo-chip`）

- [ ] **Step 1: journey.ts**

import 群の最後に:

```ts
import coverData from '../../data/journey/trip_covers.json';
```

`thumbUrl` の後に:

```ts
export interface TripCover {
  src: string;
  /** 本人の画像なら 800w・1600w。投稿のサムネで代えたときは無い */
  srcset?: string;
  own: boolean;
}

const tripCovers = (coverData as { covers: Record<string, Record<string, [number, number]>> }).covers;

/** 旅の背景画像。本人の画像（npm run journey:covers）が無ければ、旅のいちばん早い投稿のサムネで代える。 */
export function coverFor(trip: Trip): TripCover | null {
  const own = tripCovers[trip.slug];
  if (own) {
    const base = `/journey/trips/${trip.slug}`;
    return {
      src: `${base}-800.webp`,
      srcset: `${base}-800.webp ${own['800'][0]}w, ${base}-1600.webp ${own['1600'][0]}w`,
      own: true,
    };
  }
  const first = postsForTrip(trip).slice().sort((a, b) => a.date.localeCompare(b.date))[0];
  return first ? { src: thumbUrl(first), own: false } : null;
}
```

- [ ] **Step 2: global.css の末尾**

```css
/* 写真の上の文字。ライトモードの上書き（.text-white や .bg-white\/10 を黒にする）を受けない名前で、白のまま出す */
.photo-title {
  color: #f8fafc;
  text-shadow: 0 1px 4px rgb(0 0 0 / 0.6);
}
.photo-meta {
  color: rgb(248 250 252 / 0.85);
}
.photo-chip {
  color: #f8fafc;
  background: rgb(0 0 0 / 0.4);
  border: 1px solid rgb(255 255 255 / 0.25);
}
```

- [ ] **Step 3: `npm run build` が通る**（まだどこからも使っていないので見た目は変わらない）

- [ ] **Step 4: Commit**

### Task 3: `TripCard.astro` を一覧と県のページで使う

**Files:**
- Create: `src/components/journey/TripCard.astro`
- Modify: `src/pages/journey/trips/index.astro:6, 52-63, 82-93`
- Modify: `src/pages/journey/[slug].astro:71-85`

- [ ] **Step 1: 部品**

```astro
---
// 旅のカード。本人の画像（無ければ投稿のサムネ）を背景に敷き、下から暗くして文字を載せる。
// 旅の一覧（年別・地方別）と県のページ（compact）で使う。文字は global.css の photo-* で白のまま出す。
import { coverFor, formatRange, prefectureByCode, type Trip } from '../../lib/journey';

interface Props {
  trip: Trip;
  compact?: boolean;
}

const { trip, compact = false } = Astro.props;
const cover = coverFor(trip);
const prefectures = compact
  ? []
  : trip.allPrefCodes.slice(0, 5).map((code) => prefectureByCode(code)).filter(Boolean);
---

<a
  href={`/journey/trips/${trip.slug}/`}
  class:list={[
    'trip-card relative block overflow-hidden hover-lift group',
    compact ? 'rounded-xl h-28' : 'rounded-2xl h-44 md:h-48',
  ]}
>
  {cover && (
    <img
      src={cover.src}
      srcset={cover.srcset}
      sizes="(min-width: 768px) 480px, 100vw"
      alt=""
      loading="lazy"
      decoding="async"
      class="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
    />
  )}
  <div class="absolute inset-0 bg-linear-to-t from-black/75 via-black/35 to-black/5"></div>
  <div class:list={['relative h-full flex flex-col justify-end', compact ? 'p-4' : 'p-5']}>
    <div class:list={['photo-title font-semibold leading-snug line-clamp-2', compact ? 'text-sm' : 'text-base']}>
      {trip.title}
    </div>
    <div class="photo-meta text-xs mt-1">{formatRange(trip.start, trip.end)}・{trip.postCount}件</div>
    {prefectures.length > 0 && (
      <div class="flex flex-wrap gap-1 mt-2">
        {prefectures.map((prefecture) => (
          <span class="photo-chip px-2 py-0.5 rounded-full text-[10px]">{prefecture!.shortName}</span>
        ))}
      </div>
    )}
  </div>
</a>

<style>
  /* 画像が読み込まれる前と、サムネも無い旅の地の色 */
  .trip-card {
    background: #0f172a;
  }
</style>
```

- [ ] **Step 2: 旅の一覧**：52-63行と82-93行の `<a …>…</a>` をそれぞれ `<TripCard trip={trip} />` に置き換える。
  import を `import TripCard from '../../../components/journey/TripCard.astro';` と
  `import { trips, regions, regionForPrefCode } from '../../../lib/journey';` にする（`prefectureByCode`・`formatRange` は使わなくなる）

- [ ] **Step 3: 県のページ**：74-81行の `<a …>…</a>` を `<TripCard trip={trip} compact />` に置き換え、
  `import TripCard from '../../components/journey/TripCard.astro';` を足す。`formatRange` がほかで使われていなければ import から外す

- [ ] **Step 4: `npm run build` が通る。`dist/journey/trips/index.html` に `/journey/trips/2025-07-miyagi-800.webp` と `/journey/thumbs/` の両方がある**

- [ ] **Step 5: Commit**

### Task 4: 旅のページの見出し

**Files:**
- Modify: `src/pages/journey/trips/[slug].astro:6-13, 23-27, 34-40`

- [ ] **Step 1**：import に `coverFor` を足し、frontmatter に `const cover = coverFor(trip);` を足す

- [ ] **Step 2**：34-40行の `<div class="text-center mb-10">…</div>` を次に置き換える

```astro
      <div class="trip-hero relative overflow-hidden rounded-2xl h-56 md:h-72 mb-10">
        {cover && (
          <img
            src={cover.src}
            srcset={cover.srcset}
            sizes="(min-width: 1024px) 976px, 100vw"
            alt=""
            decoding="async"
            fetchpriority="high"
            class="absolute inset-0 w-full h-full object-cover"
          />
        )}
        <div class="absolute inset-0 bg-linear-to-t from-black/80 via-black/30 to-black/0"></div>
        <div class="relative h-full flex flex-col justify-end items-center text-center p-6">
          <h1 class="photo-title text-2xl md:text-3xl font-bold mb-3">{trip.title}</h1>
          <div class="flex flex-wrap justify-center gap-2 text-sm">
            <span class="photo-chip px-3 py-1 rounded-full">{formatRange(trip.start, trip.end)}</span>
            <span class="photo-chip px-3 py-1 rounded-full">{days.length}日・{posts.length}件</span>
          </div>
        </div>
      </div>
```

ファイル末尾に:

```astro
<style>
  .trip-hero {
    background: #0f172a;
  }
</style>
```

- [ ] **Step 3: `npm run build` が通る**

- [ ] **Step 4: Commit**

### Task 5: ドキュメント

**Files:**
- Modify: `README.md`（人の指定の置き場の表）、`docs/troubleshooting/TROUBLESHOOTING.md`（「旅の背景画像を足す・差し替える」）、`docs/journey/DECISIONS.md`（人が決めたこと・LLM が決めたこと）

- [ ] **Step 1**：README の表に1行

```markdown
| 旅の背景画像 | `~/dev/data/trip-covers/<slug>.<拡張子>`（リポジトリの外） | 置いてから `npm run journey:covers`。EXIF を消した webp が `public/journey/trips/` にでき、一覧が `data/journey/trip_covers.json` に入る |
```

- [ ] **Step 2**：TROUBLESHOOTING に節を足す（置き場・ファイル名・差し替えは同じ名前で置き直して流す・消すときは手で・無い旅は投稿のサムネ）

- [ ] **Step 3**：DECISIONS.md に10/08の行を足す（人: 出す場所3か所・URL 名で置く・無い旅は投稿のサムネ・届いた8件。LLM: EXIF を消す・800w/1600w・一覧を trips.json と分ける・出力は自動で消さない・見出しの帯）

- [ ] **Step 4**：日本語を gemini-3.8-flash で校正し、用語・事実のずれは戻す。Commit

### Task 6: 確かめて出す

- [ ] **Step 1**：`npm run journey:build` が何も変えない（`trip_covers.json` は同期で触られない）
- [ ] **Step 2**：プレビューで旅の一覧・旅のページ・県のページを、ダーク・ライト・スマホ幅で見る。文字が読める、画像が敷かれている、無い旅はサムネ
- [ ] **Step 3**：Fable にレビューを頼む
- [ ] **Step 4**：本人にローカルの画面を見せる（スクリーンショット）。よければ main に push し、Deploy の成功と本番を確かめる
