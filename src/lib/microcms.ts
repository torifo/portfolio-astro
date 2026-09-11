// microCMS のデータ読み出し。
//
// **ビルドは microCMS を呼ばない。** 取得は scripts/ingest/fetch_microcms.mjs が
// 先に済ませ、data/microcms/*.json に置く。ここはそれを読むだけ。
//
// 以前はビルド中に叩いており、TLS 接続が一瞬切れただけでデプロイが丸ごと落ちた
// （read ECONNRESET・全ページ生成後の最後の1本で失敗）。取得を切り離したことで、
// microCMS が落ちていても最後に取れた内容でサイトが出る。空にもならず、
// デプロイも止まらない。Journey のデータと同じ扱いに揃えてある。
//
// 手元のリポジトリには空の種ファイルが入っている（鍵が無くてもビルドが通るように）。
// CI が実データで上書きする。

import profileData from '../../data/microcms/profile.json';
import opusData from '../../data/microcms/opus.json';
import skillsData from '../../data/microcms/skills.json';
import gamesData from '../../data/microcms/games.json';

export interface HistoryEntry {
  fieldId: string;
  date: string;
  event: string;
  tag: string[];
}

export interface Profile {
  name: string;
  title: string;
  introduction: string;
  avatar: {
    url: string;
    height: number;
    width: number;
  };
  occupation_mail?: string;
  develop_mail?: string;
  history: HistoryEntry[];
}

export async function fetchProfile(): Promise<Profile | null> {
  const data = profileData as Profile & { _placeholder?: boolean };
  return data?._placeholder ? null : data;
}

export interface RelatedSkill {
  id: string;
  name: string;
  icon?: {
    url: string;
    height: number;
    width: number;
  };
  category: string[];
  level: number;
}

export interface RelatedLink {
  fieldId: string;
  service: string;
  thumbnail: {
    url: string;
    height: number;
    width: number;
  }[];
  repoUrl?: string;
  opusUrl?: string;
  context?: string;
  relatedSkill?: RelatedSkill[];
}

export interface Opus {
  id: string;
  title: string;
  description: string;
  galleryTypes: {
    url: string;
    height: number;
    width: number;
  }[];
  category: string[];
  relatedLinks: RelatedLink[];
}

export interface OpusResponse {
  contents: Opus[];
  totalCount: number;
}

export async function fetchAllOpus(): Promise<Opus[]> {
  return (opusData as OpusResponse).contents ?? [];
}

export interface Skill {
  id: string;
  createdAt: string;
  name: string;
  icon?: { url: string; height: number; width: number };
  category: string[];
  level: number;
  usedIn?: { id: string; title: string }[];
}

export function loadSkills(): Skill[] {
  return ((skillsData as { contents?: Skill[] }).contents ?? []) as Skill[];
}

export function loadGames<T>(): T[] {
  return ((gamesData as { contents?: T[] }).contents ?? []) as T[];
}

// opus.id + linkIndex から一意なslugを生成
export function generateSlug(opusId: string, linkIndex: number): string {
  return `${opusId}-${linkIndex}`;
}

// スキルカテゴリ → SkillsセクションアンカーID用スラッグ
export const SKILL_CATEGORY_SLUG: Record<string, string> = {
  'プログラミング言語': 'lang',
  'フレームワーク・ライブラリ': 'fw',
  'データベース': 'db',
  'マークアップ・スタイルシート': 'markup',
  'Web技術 / アーキテクチャ / ネットワーク': 'web',
  'デプロイ・インフラ・OS': 'deploy',
  '開発ツール・CI/CD': 'tools',
  '数値解析・自動化(マクロ)': 'analytics',
};
