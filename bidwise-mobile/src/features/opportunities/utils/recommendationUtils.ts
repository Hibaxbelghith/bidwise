import type { ProfileUser } from '@/src/features/profile/types';

import type { Opportunity, Recommendation } from '../services/opportunitiesService';

const CONFIDENCE_LABELS: Record<string, string> = {
  HIGH: 'High confidence',
  MEDIUM: 'Medium confidence',
  LOW: 'Limited profile data',
};

const FOR_YOU_PROFILE_MIN_SCORE = 40;
const FOR_YOU_PROFILE_FULL_SCORE = 70;
const FOR_YOU_MIN_MATCH_SCORE = 40;
const STRONG_MATCH_MIN_SCORE = 60;
const RECENT_COLD_PROFILE_WINDOW_MS = 30 * 60 * 1000;

const normalizeText = (value: unknown): string => String(value || '').trim();
const normalizeArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.map((item) => normalizeText(item)).filter(Boolean) : [];

const dedupe = (items: string[]): string[] => {
  const seen = new Set<string>();
  const result: string[] = [];

  for (const item of items) {
    const key = item.toLowerCase();
    if (!item || seen.has(key)) continue;
    seen.add(key);
    result.push(item);
  }

  return result;
};

const humanizeReason = (reason: string): string => {
  const text = normalizeText(reason);
  if (!text) return '';
  if (text === 'Role alignment detected') return 'Role aligned';
  if (text === 'Title language overlaps your goals') return 'Title aligns with your goals';
  if (text === 'Industry preference aligned') return 'Industry aligned';
  if (text === 'Resume signal detected') return 'CV signal detected';
  if (text === 'Semantic similarity is strong') return 'Strong profile similarity';
  if (text === 'Related job family signal detected') return 'Related job category';
  return text;
};

const buildStructuredReasons = (recommendation: Recommendation): string[] => {
  const evidence = recommendation.evidence_summary || {};
  const reasons: string[] = [];

  if (evidence.role_match) reasons.push('Role aligned');
  if (Number(evidence.skill_overlap || evidence.profile_skill_overlap || 0) > 0) {
    reasons.push('Matching skills');
  }
  if (evidence.resume_signal) reasons.push('CV signal detected');
  if (evidence.title_overlap) reasons.push('Title aligns with your goals');
  if (evidence.industry_match) reasons.push('Industry aligned');
  if (normalizeText(evidence.semantic_strength).toLowerCase() === 'strong') {
    reasons.push('Strong profile similarity');
  }
  if (evidence.llm_family_match) reasons.push('Related job category');

  return reasons;
};

export type RecommendationSignalChip = {
  key: string;
  label: string;
};

export type ForYouProfileTier = 'insufficient' | 'partial' | 'complete';

export function isCallsForTenderOnlyUser(user: ProfileUser | null | undefined): boolean {
  const types = normalizeArray(user?.profil?.opportunity_types).map((item) => item.toUpperCase());
  return types.length === 1 && types[0] === 'CALLS_FOR_TENDER';
}

export function hasTenderRecommendationPreferences(user: ProfileUser | null | undefined): boolean {
  const profile = user?.profil;
  const regions = normalizeArray(profile?.preferred_locations);
  const categories = Array.isArray(profile?.tender_preferences?.categories)
    ? profile.tender_preferences.categories
    : [];

  return regions.length > 0 && categories.length > 0;
}

export function getRecommendationScorePercent(value: unknown): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;

  const normalized = parsed > 1 ? parsed / 100 : parsed;
  return Math.round(Math.max(0, Math.min(normalized, 1)) * 100);
}

export function getProfileCompletionScore(user: ProfileUser | null | undefined): number {
  const score = Number(user?.profil?.profile_completion?.score);
  return Number.isFinite(score) ? Math.max(0, Math.min(score, 100)) : 0;
}

export function getProfileRecommendationTier(
  user: ProfileUser | null | undefined,
): ForYouProfileTier {
  if (isCallsForTenderOnlyUser(user)) {
    return hasTenderRecommendationPreferences(user) ? 'complete' : 'insufficient';
  }

  const score = getProfileCompletionScore(user);
  if (score < FOR_YOU_PROFILE_MIN_SCORE) return 'insufficient';
  if (score <= FOR_YOU_PROFILE_FULL_SCORE) return 'partial';
  return 'complete';
}

export function isFallbackRecommendation(recommendation: Recommendation | null | undefined): boolean {
  const mode = normalizeText(recommendation?.recommendation_mode).toUpperCase();
  const label = normalizeText(recommendation?.score_label).toLowerCase();

  return mode === 'FALLBACK' || label === 'recent';
}

export function isQualifiedRecommendation(
  recommendation: Recommendation | null | undefined,
  minScore = FOR_YOU_MIN_MATCH_SCORE,
): boolean {
  if (!recommendation || isFallbackRecommendation(recommendation)) return false;

  const scorePercent = getRecommendationScorePercent(
    recommendation.score ?? recommendation.match_score,
  );
  return scorePercent !== null && scorePercent >= minScore;
}

export function isStrongMatchRecommendation(
  recommendation: Recommendation | null | undefined,
): boolean {
  if (!recommendation) return false;

  const bucket = normalizeText(recommendation.recommendation_bucket).toUpperCase();
  if (bucket) return bucket === 'STRONG_MATCH';

  const scorePercent = getRecommendationScorePercent(
    recommendation.score ?? recommendation.match_score,
  );
  return scorePercent !== null && scorePercent >= STRONG_MATCH_MIN_SCORE;
}

export function getRecommendationConfidenceLabel(
  recommendation: Recommendation | null | undefined,
): string {
  const type = normalizeText(recommendation?.type_opportunite || recommendation?.type).toUpperCase();
  if (type === 'PROJET') {
    const scorePercent = getRecommendationScorePercent(
      recommendation?.score ?? recommendation?.match_score,
    );
    if (scorePercent !== null && scorePercent >= 60) return 'Strong priority';
    if (scorePercent !== null && scorePercent >= 40) return 'Review priority';
    return 'Low priority';
  }

  const key = normalizeText(recommendation?.recommendation_confidence).toUpperCase();
  return CONFIDENCE_LABELS[key] || 'Confidence improving';
}

export function getRecommendationReasons(
  recommendation: Recommendation | null | undefined,
  limit = 3,
): string[] {
  if (!recommendation) return [];

  const reasons = [
    ...buildStructuredReasons(recommendation),
    ...normalizeArray(recommendation.reasons || recommendation.reason).map(humanizeReason),
  ].filter(Boolean);

  return dedupe(reasons).slice(0, limit);
}

export function getRecommendationSignalChips(
  recommendation: Recommendation | null | undefined,
): RecommendationSignalChip[] {
  if (!recommendation) return [];

  const type = normalizeText(recommendation.type_opportunite || recommendation.type).toUpperCase();
  if (type === 'PROJET') {
    const reasons = normalizeArray(recommendation.reasons || recommendation.reason);
    const chips: RecommendationSignalChip[] = [];
    if (reasons.some((reason) => /subcategory/i.test(reason))) {
      chips.push({ key: 'category', label: 'Category' });
    } else if (reasons.some((reason) => /category/i.test(reason))) {
      chips.push({ key: 'category', label: 'Category' });
    }
    if (reasons.some((reason) => /region/i.test(reason))) {
      chips.push({ key: 'region', label: 'Region' });
    }
    if (reasons.some((reason) => /semantic/i.test(reason))) {
      chips.push({ key: 'semantic', label: 'Similarity' });
    }
    return chips.slice(0, 3);
  }

  const evidence = recommendation.evidence_summary || {};
  const chips: RecommendationSignalChip[] = [];
  const add = (key: string, label: string) => {
    if (!chips.some((chip) => chip.key === key)) chips.push({ key, label });
  };

  if (evidence.role_match) add('role', 'Role');
  if (Number(evidence.skill_overlap || evidence.profile_skill_overlap || 0) > 0) {
    add('skills', 'Skills');
  }
  if (evidence.resume_signal) add('cv', 'CV');
  if (evidence.title_overlap) add('title', 'Title');
  if (evidence.industry_match) add('industry', 'Industry');
  if (normalizeText(evidence.semantic_strength).toLowerCase() === 'strong') {
    add('semantic', 'Similarity');
  }

  return chips.slice(0, 3);
}

export function recommendationToOpportunity(recommendation: Recommendation): Opportunity {
  return {
    ...recommendation,
    titre: recommendation.title || recommendation.titre || '',
    organisation_nom: recommendation.company || recommendation.organisation_nom || '',
    ville: recommendation.location || recommendation.ville || '',
    type_opportunite: recommendation.type || recommendation.type_opportunite || '',
    recommendation,
  };
}

export function isResumeStillPreparing(user: ProfileUser | null | undefined): boolean {
  const resume = user?.profil?.active_resume;
  if (!resume) return false;

  const parsingStatus = normalizeText(resume.parsing_status).toUpperCase();
  const semanticStatus = normalizeText(resume.semantic_resume_status).toUpperCase();

  return (
    parsingStatus === 'PENDING' ||
    parsingStatus === 'PROCESSING' ||
    semanticStatus === 'PENDING' ||
    semanticStatus === 'PROCESSING'
  );
}

export function isColdProfileRecommendationState(
  user: ProfileUser | null | undefined,
  recommendations: Recommendation[],
): boolean {
  if (recommendations.length > 0) return false;
  if (getProfileRecommendationTier(user) === 'insufficient') return false;
  if (isResumeStillPreparing(user)) return true;

  const resumeUploadedAt = normalizeText(user?.profil?.active_resume?.uploaded_at);
  if (!resumeUploadedAt) return false;

  const uploadedAt = new Date(resumeUploadedAt);
  if (Number.isNaN(uploadedAt.getTime())) return false;

  return Date.now() - uploadedAt.getTime() <= RECENT_COLD_PROFILE_WINDOW_MS;
}
