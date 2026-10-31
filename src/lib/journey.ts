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
import workCoverData from '../../data/journey/work_covers.json';
import workLinkData from '../../data/journey/work_links.json';

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
  /** Instagram に投稿した日時（2026-10-05T22:52:00+09:00）。撮影日の date とは別 */
  uploaded_at: string;
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
  /** 期間つきの旅。同じタグを別の時期にも付けているので、期間（start〜end）の中の投稿だけを入れる（build_trips.py） */
  window?: boolean;
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
  const inWindow = (p: Post) => !trip.window || (p.date >= trip.start && p.date <= trip.end);
  return posts.filter((p) => p.hashtags.some((t) => tags.has(t)) && inWindow(p));
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

const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * 県のページの見出しの下に出すエリア。投稿の1行目（日付の行）に「北海道(旭川)」のように書いたエリアを、多い順に並べる
 * （2026-10-31 本人「北海道（エリア）で書いてるものがあるからエリアを書けばいい」）。エリアを書いた投稿が無い県は空で、
 * ページは手で書いた note を出す（過去の投稿にエリアは足さない）。
 */
export function areasForPrefecture(prefecture: Prefecture, list: Post[]): string[] {
  const names = [...new Set([prefecture.name, prefecture.shortName])].map(escapeRegExp).join('|');
  const pattern = new RegExp(`(?:${names})[（(]([^）)]+)[）)]`, 'g');
  const counts = new Map<string, number>();
  for (const post of list) {
    const first = post.caption.split('\n')[0];
    if (!/^\d{4}-\d{2}-\d{2}/.test(first)) continue;
    for (const match of first.matchAll(pattern)) {
      for (const area of match[1].split(/[・、,，/]/).map((a) => a.trim()).filter(Boolean)) {
        counts.set(area, (counts.get(area) ?? 0) + 1);
      }
    }
  }
  return [...counts].sort((a, b) => b[1] - a[1]).map(([area]) => area);
}

// ハイライトに出さないタグ：旅の名前（長い一文）、都道府県の名前、伏せた作品（hidden）の名前
const NOT_HIGHLIGHT = new Set<string>([
  ...(tripData.trips as Trip[]).flatMap((t) => [t.tag, t.title]),
  ...prefectures.flatMap((p) => [p.name, p.shortName]),
  ...(pilgrimageData.works as Work[]).filter((w) => w.hidden).flatMap((w) => [w.title, ...(w.aliases ?? [])]),
]);

/**
 * 県のハイライト。その県の投稿でよく付けたタグを、多い順に件数つきで出す（2回以上・最大 limit 個）。
 * 以前は料理の言葉（カフェ・丼など）で「この県で食べたもの」を拾っていて、「ネカフェ」がカフェに当たった
 * （2026-10-31 本人「ハイライトとかタグ数で出すなら良さそう」）。
 */
export function highlightTags(list: Post[], limit = 10): { tag: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const post of list) {
    for (const tag of new Set(post.hashtags)) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  }
  return [...counts]
    .filter(([tag, count]) => count >= 2 && !NOT_HIGHLIGHT.has(tag))
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([tag, count]) => ({ tag, count }));
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
  /**
   * 余白に敷く画像（本人の画像だけ）。端を鏡に映して上下左右に 0.75 倍ずつ延ばしてあるので、
   * 手前の画像の 250% の大きさで中央に重ねると、延ばした部分が手前の画像の端から続く（build_trip_covers.py）
   */
  fill?: string;
  /** 本人の画像の幅÷高さ。旅のページの見出しで、画像と同じ形の枠を作るのに使う */
  ratio?: number;
  own: boolean;
  /**
   * 4:3 のカードにどう収めるか。どの形でも画像は全体を見せる。
   * fit: ほぼ 4:3 なのでカードいっぱいに敷く／wide: 4:3 より横長なので幅に合わせ、上下を同じ画像のぼかしでつなぐ／
   * tall: 正方形などなので高さに合わせ、左右をぼかしでつなぐ
   */
  shape: 'fit' | 'wide' | 'tall';
}

function shapeOf(width: number, height: number): TripCover['shape'] {
  const ratio = width / height;
  if (Math.abs(ratio - 4 / 3) < 0.02) return 'fit';
  return ratio > 4 / 3 ? 'wide' : 'tall';
}

const tripCovers = (coverData as { covers: Record<string, Record<string, [number, number]>> }).covers;

/**
 * 旅の背景画像。本人の画像（npm run journey:covers）が無ければ、旅のいちばん新しく投稿したもののサムネで代える。
 * 本人は旅の投稿を終えてから画像を作るので、それまでは投稿が増えるたびに最新のものが出る。
 */
export function coverFor(trip: Trip): TripCover | null {
  const own = tripCovers[trip.slug];
  if (own) {
    const base = `/journey/trips/${trip.slug}`;
    return {
      src: `${base}-800.webp`,
      srcset: `${base}-800.webp ${own['800'][0]}w, ${base}-1600.webp ${own['1600'][0]}w`,
      fill: `${base}-fill.webp`,
      ratio: own['800'][0] / own['800'][1],
      own: true,
      shape: shapeOf(own['800'][0], own['800'][1]),
    };
  }
  const latest = postsForTrip(trip).slice().sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at))[0];
  return latest ? { src: thumbUrl(latest), own: false, shape: 'tall' } : null;
}

export interface WorkCover extends TripCover {
  /** 画像の出典の表示（「写真：作者 / CC BY-SA 4.0」「© 作品の権利者」）。本人の画像には無い */
  credit?: string;
  /** 出典のページ（作品のページのクレジットからリンクする） */
  source?: string;
  /** 一覧の帯での置き方。cover＝帯いっぱいに切り取る／fit＝全体を見せて余白をぼかす。無ければ形で決める */
  mode?: 'cover' | 'fit';
  /** 帯で切り取るときの中心（CSS の object-position）。無ければ中央 */
  focus?: string;
}

type WorkCoverEntry = Record<string, [number, number]> & { credit?: string; source?: string; mode?: 'cover' | 'fit'; focus?: string };
const workCovers = (workCoverData as { covers: Record<string, WorkCoverEntry> }).covers;

/**
 * 聖地巡礼の作品の背景画像。用意した画像（npm run journey:work-covers）が無ければ、作品のいちばん新しく投稿したもののサムネで代える。
 * 画像は旅の画像と同じ形（800w・1600w・余白用の fill）なので、旅の見出しと同じ作りで出せる。
 */
export function workCoverFor(work: Work): WorkCover | null {
  const own = workCovers[work.slug];
  if (own) {
    const base = `/journey/works/${work.slug}`;
    return {
      src: `${base}-800.webp`,
      srcset: `${base}-800.webp ${own['800'][0]}w, ${base}-1600.webp ${own['1600'][0]}w`,
      fill: `${base}-fill.webp`,
      ratio: own['800'][0] / own['800'][1],
      own: true,
      shape: shapeOf(own['800'][0], own['800'][1]),
      credit: own.credit,
      source: own.source,
      mode: own.mode,
      focus: own.focus,
    };
  }
  const latest = postsForWork(work).slice().sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at))[0];
  return latest ? { src: thumbUrl(latest), own: false, shape: 'tall' } : null;
}

/** 作品の公式リンク（data/journey/work_links.json）。作品のページに PV と投稿を埋め込む */
export interface WorkLinks {
  youtube?: { id: string; title: string; channel: string };
  x?: { handle: string; post?: string | null };
  officialSite?: string;
  /** 公式サイトのカード。image はサイトの og:image（公式サイトから直接出す） */
  site?: { title: string; image?: string };
}

const workLinks = (workLinkData as { links: Record<string, WorkLinks> }).links;

export function workLinksFor(work: Work): WorkLinks {
  return workLinks[work.slug] ?? {};
}

// 題名の折り返し位置。日本語は既定だとどの文字の間でも折り返すので、「伊勢志 / 摩」のように単語の途中で切れる。
// word-break: auto-phrase は Chrome だけなので使わず、ビルドのときに単語の区切りを出し、その間にだけ <wbr> を置く（CSS は keep-all）。
// 区切りは Intl.Segmenter（ICU の辞書）。ただしカタカナ・平仮名の語を割ることがある（サン|ラ|イズ、シ|ャ|トレー|ゼ）ので、次では区切らない
const wordSegmenter = new Intl.Segmenter('ja', { granularity: 'word' });
const HIRAGANA_START = /^[\u3041-\u309f]/;
const KATAKANA_START = /^[\u30a1-\u30ff]/;
const KATAKANA_END = /[\u30a1-\u30ff]$/;
const LINE_START_NG = /^[ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶー]/;
const DIGIT_END = /[0-9０-９]$/;
const PARTICLES = new Set(['の', 'へ', 'を', 'に', 'が', 'と', 'で', 'は', 'も', 'や', 'から', 'まで', 'より']);

function breakableBetween(a: string, b: string): boolean {
  const lengthOf = (s: string) => [...s].length;
  if (LINE_START_NG.test(b) || DIGIT_END.test(a)) return false; // 行頭の小さい仮名・長音、数字と助数詞（2泊・3度目）
  // 助詞の後に2文字以上の語が続くなら区切ってよい。次の決まりより先に見る（「ラブコメは / まちがっている」の「まち」は短い平仮名だった）
  if (PARTICLES.has(a) && !PARTICLES.has(b) && lengthOf(b) >= 2) return true;
  if (HIRAGANA_START.test(b) && lengthOf(b) <= 2) return false; // 助詞・送り仮名は前の言葉に付ける
  if (lengthOf(b) < 2) return false; // 1文字の断片（旅・編・巻・市、割れた語）は前に付ける
  if (PARTICLES.has(a)) return true; // 助詞の後は区切ってよい（松島への / 往復）
  if (lengthOf(a) < 2) return false; // 1文字の断片は後ろにも付ける（鳩ノ巣、初首都高）
  if (KATAKANA_END.test(a) && KATAKANA_START.test(b) && (lengthOf(a) < 3 || lengthOf(b) < 3)) return false; // 短いカタカナどうし（インスパ）
  return true;
}

/** 題名を、折り返してよい位置で区切った塊にする（間に <wbr> を置いて使う）。 */
export function titleChunks(title: string): string[] {
  const parts = [...wordSegmenter.segment(title)].map((s) => s.segment);
  const chunks = parts.length ? [parts[0]] : [];
  for (let i = 1; i < parts.length; i++) {
    if (breakableBetween(parts[i - 1], parts[i])) chunks.push(parts[i]);
    else chunks[chunks.length - 1] += parts[i];
  }
  return chunks;
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
