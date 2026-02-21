// microCMS API ユーティリティ

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
  const MICROCMS_API_KEY = import.meta.env.PUBLIC_MICROCMS_API_KEY;
  const SERVICE_DOMAIN = import.meta.env.PUBLIC_MICROCMS_SERVICE_DOMAIN;

  const response = await fetch(`${SERVICE_DOMAIN}opus?limit=100&orders=createdAt`, {
    headers: { 'X-MICROCMS-API-KEY': MICROCMS_API_KEY },
  });

  if (!response.ok) return [];
  const data: OpusResponse = await response.json();
  return data.contents;
}

// opus.id + linkIndex から一意なslugを生成
export function generateSlug(opusId: string, linkIndex: number): string {
  return `${opusId}-${linkIndex}`;
}
