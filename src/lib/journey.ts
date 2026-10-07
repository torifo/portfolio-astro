// Journey（Instagram 連携）のビルド時データ。
//
// 判定は scripts/journey/ 側で済ませてあり、ここは読み出すだけ。サイトの
// ビルドは外部サービスを一切呼ばない。data/journey/*.json を作り直す手順は
// data/ontology/README.md を参照。

import prefectureData from '../../data/journey/prefectures.json';
import postData from '../../data/journey/posts.json';
import resolvedData from '../../data/journey/resolved.json';
import tripData from '../../data/journey/trips.json';
import pilgrimageData from '../../data/journey/pilgrimages.json';
import permalinkData from '../../data/journey/permalinks.json';
import themeData from '../../data/journey/themes.json';
import coverData from '../../data/journey/trip_covers.json';

export interface Prefecture {
  code: string;
  name: string;
  shortName: string;
  slug: string;
  visited: boolean;
  note?: string;
}

export interface Region {
  name: string;
  en: string;
  gradient: string;
  prefectures: Prefecture[];
}

export interface Post {
  id: string;
  kind: string;
  date: string;
  datePrecision: string;
  caption: string;
  hashtags: string[];
  cover: string | null;
  media: string[];
}

export interface Trip {
  slug: string;
  tag: string;
  title: string;
  start: string;
  end: string;
  postCount: number;
  prefCodes: string[];
  allPrefCodes: string[];
  spots: string[];
  hidden?: boolean;
}

export interface Work {
  slug: string;
  title: string;
  aliases: string[];
  postCount: number;
  start: string;
  end: string;
  prefCodes: string[];
  postIds: string[];
  hidden?: boolean;
  /** 作品名の無い聖地巡礼をまとめた枠（作品数には数えない） */
  untitled?: boolean;
}

export interface Theme {
  slug: string;
  title: string;
  lead?: string;
  tags: string[];
  postCount: number;
  prefCodes: string[];
  postIds: string[];
  hidden?: boolean;
}

type RawPost = Post & { date_precision: string };
type Resolution = { prefCodes: string[] | null; method: string | null; evidence: unknown; hidden?: boolean };

export const regions: Region[] = prefectureData.regions as Region[];
export const prefectures: Prefecture[] = regions.flatMap((r) => r.prefectures);
export const trips: Trip[] = (tripData.trips as Trip[]).filter((t) => !t.hidden);
// pilgrimages.json の works は作品の辞書も兼ねるので、投稿がまだ無い作品も入っている
export const works: Work[] = (pilgrimageData.works as Work[]).filter((w) => !w.hidden && w.postCount > 0);
/** 作品数。「作品名なし」の枠は数えない。 */
export const workCount = works.filter((w) => !w.untitled).length;
// テーマ軸。被写体でまとめる4つめの軸で、県・旅・聖地巡礼と重ね掛けになる。
// 県が特定できない投稿もここには出せる（空の写真は場所が分からなくても空の記録）。
export const themes: Theme[] = (themeData.themes as Theme[]).filter((t) => !t.hidden);

const resolutions = resolvedData.posts as Record<string, Resolution>;

// 日付の後ろに「趣味」と書いた投稿（hidden）はサイトのどこにも出さない
export const posts: Post[] = (postData.posts as RawPost[])
  .filter((p) => !resolutions[p.id]?.hidden)
  .map((p) => ({
    ...p,
    datePrecision: p.date_precision,
  }));

const postsById = new Map(posts.map((p) => [p.id, p]));

/** 都道府県コードから、それが属する地方（8地方）を引く。 */
export function regionForPrefCode(code: string): Region | undefined {
  return regions.find((region) => region.prefectures.some((p) => p.code === code));
}

export function prefectureBySlug(slug: string): Prefecture | undefined {
  return prefectures.find((p) => p.slug === slug);
}

export function prefectureByCode(code: string): Prefecture | undefined {
  return prefectures.find((p) => p.code === code);
}

/** 県コードから、その県に属する投稿を新しい順で返す。県をまたぐ投稿は両方に出る。 */
export function postsForPrefecture(code: string): Post[] {
  return posts.filter((p) => resolutions[p.id]?.prefCodes?.includes(code));
}

export function postsForTrip(trip: Trip): Post[] {
  const tags = new Set([trip.tag, ...trip.spots]);
  return posts.filter((p) => p.hashtags.some((t) => tags.has(t)));
}

export function postsForWork(work: Work): Post[] {
  return work.postIds.map((id) => postsById.get(id)).filter((p): p is Post => Boolean(p));
}

export function postsForTheme(theme: Theme): Post[] {
  return theme.postIds.map((id) => postsById.get(id)).filter((p): p is Post => Boolean(p));
}

export function themesForPrefecture(code: string): Theme[] {
  return themes.filter((t) => t.prefCodes.includes(code));
}

export function prefCodesFor(post: Post): string[] {
  return resolutions[post.id]?.prefCodes ?? [];
}

/** 投稿件数。県ページを出すかどうかと、地方ごとの見出しに使う。 */
export const postCountByPrefecture: Record<string, number> = (() => {
  const counts: Record<string, number> = {};
  for (const prefecture of prefectures) counts[prefecture.code] = 0;
  for (const post of posts) {
    for (const code of resolutions[post.id]?.prefCodes ?? []) {
      if (code in counts) counts[code] += 1;
    }
  }
  return counts;
})();

export function tripsForPrefecture(code: string): Trip[] {
  return trips.filter((t) => t.allPrefCodes.includes(code));
}

export function worksForPrefecture(code: string): Work[] {
  return works.filter((w) => w.prefCodes.includes(code));
}

export const INSTAGRAM_HANDLE = 'a_traveler_who_pursue_nature';
export const INSTAGRAM_PROFILE = `https://www.instagram.com/${INSTAGRAM_HANDLE}/`;

const permalinks = permalinkData as Record<string, string>;

/**
 * 投稿に対応する Instagram のURL。
 *
 * データエクスポートには自分の投稿の permalink が含まれない。media id から
 * ショートコードを計算する方法は使えない（エクスポートの id は Graph API の
 * media id で、ショートコードの元になる内部 pk とは別物。試すと2015年形式の
 * 10文字が出てきて実在しない）。埋まるまではプロフィールへ飛ばす。
 */
export function instagramUrl(post: Post): string {
  return permalinks[post.id] ?? INSTAGRAM_PROFILE;
}

export function hasPermalink(post: Post): boolean {
  return Boolean(permalinks[post.id]);
}

/** 表紙サムネのURL。scripts/ingest/build_thumbs.py が public/journey/thumbs へ出す。 */
export function thumbUrl(post: Post): string {
  return `/journey/thumbs/${post.id}.webp`;
}

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

/**
 * 「2025年6月15日」。月までしか分からない投稿は「2025年6月」、年までは「2022年」。
 * 撮影日が分からない投稿（date は投稿日で、並び順のためだけにある）は「日付不明」。
 */
export function formatDate(date: string, precision = 'day'): string {
  const [year, month, day] = date.split('-');
  if (precision === 'unknown') return '日付不明';
  if (precision === 'year') return `${year}年`;
  return precision === 'month' ? `${year}年${Number(month)}月` : `${year}年${Number(month)}月${Number(day)}日`;
}

/** 撮影した年が分かる投稿か（県・テーマのページの「2023年〜2025年」に数える）。 */
export function hasYear(post: Post): boolean {
  return post.datePrecision !== 'unknown';
}

/** 撮影した日が分かる投稿か（旅の「N日」に数える）。 */
export function hasDay(post: Post): boolean {
  return post.datePrecision !== 'unknown' && post.datePrecision !== 'year';
}

/**
 * 「2025年6月15日」「2025年6月15日〜17日」「2024年9月2日〜2025年4月27日」。
 * 同じ年・同じ月の部分は繰り返さない。日本語では〜の前後に空白を入れない。
 */
export function formatRange(start: string, end: string): string {
  if (start === end) return formatDate(start);

  const [startYear, startMonth] = start.split('-');
  const [endYear, endMonth, endDay] = end.split('-');

  if (startYear !== endYear) return `${formatDate(start)}〜${formatDate(end)}`;
  if (startMonth !== endMonth) return `${formatDate(start)}〜${Number(endMonth)}月${Number(endDay)}日`;
  return `${formatDate(start)}〜${Number(endDay)}日`;
}
