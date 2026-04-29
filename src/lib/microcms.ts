// microCMS API ユーティリティ

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

let _profilePromise: Promise<Profile | null> | null = null;

export function fetchProfile(): Promise<Profile | null> {
  if (!_profilePromise) {
    const MICROCMS_API_KEY = import.meta.env.PUBLIC_MICROCMS_API_KEY;
    const SERVICE_DOMAIN = import.meta.env.PUBLIC_MICROCMS_SERVICE_DOMAIN;
    _profilePromise = fetch(`${SERVICE_DOMAIN}profile`, {
      headers: { 'X-MICROCMS-API-KEY': MICROCMS_API_KEY },
    }).then(r => r.ok ? r.json() : null).catch(() => null);
  }
  return _profilePromise;
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

let _opusPromise: Promise<Opus[]> | null = null;

export function fetchAllOpus(): Promise<Opus[]> {
  if (!_opusPromise) {
    const MICROCMS_API_KEY = import.meta.env.PUBLIC_MICROCMS_API_KEY;
    const SERVICE_DOMAIN = import.meta.env.PUBLIC_MICROCMS_SERVICE_DOMAIN;
    _opusPromise = fetch(`${SERVICE_DOMAIN}opus?limit=100&orders=createdAt`, {
      headers: { 'X-MICROCMS-API-KEY': MICROCMS_API_KEY },
    }).then(r => {
      if (!r.ok) return [];
      return r.json().then((data: OpusResponse) => data.contents);
    }).catch(() => []);
  }
  return _opusPromise;
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
