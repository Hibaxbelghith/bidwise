import type {
  Opportunity,
  OpportunityExtraData,
  SimilarOpportunity,
} from '../services/opportunitiesService';
import { formatExperienceLabel, formatProjectDocumentType } from './opportunityFormatters';

export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export function getErrorMessage(error: unknown): string {
  const maybeError = error as {
    response?: {
      data?: unknown;
    };
  };

  const payload = maybeError.response?.data;
  if (typeof payload === 'object' && payload !== null) {
    const detail = (payload as Record<string, unknown>).detail;
    const message = (payload as Record<string, unknown>).error;

    if (typeof detail === 'string' && detail.trim()) return detail;
    if (typeof message === 'string' && message.trim()) return message;
  }

  return 'Unable to load opportunities right now.';
}

export function dedupeStrings(values: unknown): string[] {
  if (!Array.isArray(values)) return [];

  const deduped: string[] = [];
  const seen = new Set<string>();

  for (const rawValue of values) {
    const cleanValue = String(rawValue || '').trim();
    if (!cleanValue) continue;

    const key = cleanValue.toLowerCase();
    if (seen.has(key)) continue;

    seen.add(key);
    deduped.push(cleanValue);
  }

  return deduped;
}

export function hasDisplayValue(value: unknown): boolean {
  if (Array.isArray(value)) return dedupeStrings(value).length > 0;
  if (value && typeof value === 'object') {
    return Object.keys(value as Record<string, unknown>).length > 0;
  }

  return Boolean(String(value || '').trim());
}

export function formatDisplayValue(value: unknown): string {
  if (Array.isArray(value)) return dedupeStrings(value).join(', ');
  if (value && typeof value === 'object') return '';
  return String(value || '').trim();
}

export function getLanguagesLabel(item: Opportunity): string {
  return formatDisplayValue(item.languages || item.languages_fallback || []);
}

export function getExtraData(item: Opportunity | null): OpportunityExtraData {
  if (!item?.extra_data || typeof item.extra_data !== 'object') {
    return {};
  }

  return item.extra_data;
}

export function buildAdditionalInfoItems(extraData: OpportunityExtraData) {
  const fields: [string, unknown][] = [
    ['Sector', extraData.company_sector],
    ['Company size', extraData.company_size],
    ['Reference', extraData.reference],
    ['Experience', extraData.experience_text],
    ['Contract types', extraData.contract_types],
    ['Education levels', extraData.education_levels],
    ['Qualifications', extraData.job_qualifications],
  ];

  return fields
    .map(([label, value]) => ({ label, value: formatDisplayValue(value) }))
    .filter((item) => item.value);
}

export function getProjectDocuments(item: Opportunity | null) {
  const extraData = getExtraData(item);
  const documents: { url: string; type: string; label: string }[] = [];
  const seenUrls = new Set<string>();

  const pushDocument = (url: unknown, type: unknown, label: unknown) => {
    const normalizedUrl = String(url || '').trim();
    if (!normalizedUrl || seenUrls.has(normalizedUrl)) return;

    documents.push({
      url: normalizedUrl,
      type: String(type || '').trim() || 'autres',
      label:
        String(label || '').trim() ||
        formatProjectDocumentType(String(type || '').trim(), String(label || '').trim()),
    });
    seenUrls.add(normalizedUrl);
  };

  if (Array.isArray(extraData.documents)) {
    extraData.documents.forEach((document) => {
      if (!document || typeof document !== 'object') return;
      pushDocument(document.url, document.type, document.label);
    });
  }

  pushDocument(extraData.cahier_des_charges_url, 'cahier_des_charges', 'Cahier des charges');
  pushDocument(extraData.pdf_url, 'avis_appel_offres', "Avis d'appel d'offres");

  return documents;
}

export function dedupeSimilarItems(
  items: SimilarOpportunity[],
  currentId: number,
): SimilarOpportunity[] {
  const byId = new Set<number>();
  const byTitle = new Set<string>();
  const result: SimilarOpportunity[] = [];

  for (const item of items || []) {
    if (!item?.id || Number(item.id) === Number(currentId)) continue;
    if (byId.has(item.id)) continue;

    const normalizedTitle = String(item.titre || '').trim().toLowerCase();
    if (normalizedTitle && byTitle.has(normalizedTitle)) continue;

    byId.add(item.id);
    if (normalizedTitle) byTitle.add(normalizedTitle);
    result.push(item);
  }

  return result;
}

export function computeSemanticMatchScore(items: SimilarOpportunity[]): number | null {
  const scores = (items || [])
    .map((item) => Number(item?.similarity_score))
    .filter((value) => Number.isFinite(value));

  if (!scores.length) return null;
  return Math.round(Math.max(...scores) * 100);
}

export function hasOpportunityRecommendationSignal(item: Opportunity): boolean {
  return Boolean(
    item.recommendation ||
      item.score_label ||
      item.recommendation_confidence ||
      item.recommendation_mode ||
      item.recommendation_bucket ||
      item.recommendation_bucket_reason ||
      item.tender_recommendation,
  );
}

export function getOpportunityMatchScorePercent(item: Opportunity): number | null {
  if (!hasOpportunityRecommendationSignal(item)) return null;

  const candidates = [item.score, item.match_score, item.semantic_score, item.similarity_score];

  for (const candidate of candidates) {
    const parsed = Number(candidate);
    if (!Number.isFinite(parsed)) continue;
    const normalized = parsed > 1 ? parsed / 100 : parsed;
    return Math.round(Math.max(0, Math.min(normalized, 1)) * 100);
  }

  return null;
}

export function buildMatchBullets(item: Opportunity, score: number | null): string[] {
  const bullets: string[] = [];
  const coreSkills = dedupeStrings(item.skills).slice(0, 3);
  const location = String(item.ville || '').trim();
  const experience = formatExperienceLabel(item);

  if (coreSkills.length) {
    bullets.push(`Skills fit: ${coreSkills.join(', ')}`);
  }
  if (experience) {
    bullets.push(`Experience fit: ${experience}`);
  }
  if (location) {
    bullets.push(`Location fit: ${location}`);
  }
  if (score !== null) {
    bullets.push(`Semantic score: ${score}%`);
  }

  if (!bullets.length) {
    bullets.push('Baseline relevance detected by BidWise.');
  }

  return bullets.slice(0, 3);
}
