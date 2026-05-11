const CONFIDENCE_LABELS = {
  HIGH: 'High confidence',
  MEDIUM: 'Medium confidence',
  LOW: 'Limited profile data',
};

const SCORE_LEVELS = {
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW: 'LOW',
  TRENDING: 'TRENDING',
};

const normalizeText = (value) => String(value || '').trim();

const normalizeArray = (value) => {
  if (!Array.isArray(value)) return [];
  return value.map(normalizeText).filter(Boolean);
};

export const FOR_YOU_PROFILE_MIN_SCORE = 40;
export const FOR_YOU_PROFILE_FULL_SCORE = 70;
export const FOR_YOU_MIN_MATCH_SCORE = 40;

const dedupe = (items) => {
  const seen = new Set();
  const result = [];

  for (const item of items || []) {
    const text = normalizeText(item);
    const key = text.toLowerCase();
    if (!text || seen.has(key)) continue;
    seen.add(key);
    result.push(text);
  }

  return result;
};

export const getRecommendationScorePercent = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;

  const normalized = parsed > 1 ? parsed / 100 : parsed;
  return Math.round(Math.max(0, Math.min(normalized, 1)) * 100);
};

export const getRecommendationLevel = (recommendation) => {
  const explicitLevel = normalizeText(recommendation?.score_level).toUpperCase();
  if (explicitLevel) return explicitLevel;

  const scorePercent = getRecommendationScorePercent(
    recommendation?.score ?? recommendation?.match_score,
  );
  if (scorePercent === null) return SCORE_LEVELS.LOW;
  if (scorePercent >= 80) return SCORE_LEVELS.HIGH;
  if (scorePercent >= 60) return SCORE_LEVELS.MEDIUM;
  if (scorePercent <= 0 && normalizeText(recommendation?.score_label).toLowerCase() === 'recent') {
    return SCORE_LEVELS.TRENDING;
  }
  return SCORE_LEVELS.LOW;
};

export const getRecommendationTone = (recommendation) => {
  const level = getRecommendationLevel(recommendation);

  if (level === SCORE_LEVELS.HIGH) {
    return {
      badge: 'border-emerald-200 bg-emerald-50 text-emerald-800',
      ring: '#10b981',
      panel: 'border-emerald-100 bg-white',
      icon: 'bg-emerald-100 text-emerald-700',
      text: 'text-emerald-700',
      surface: 'bg-emerald-50 text-emerald-800',
    };
  }

  if (level === SCORE_LEVELS.MEDIUM) {
    return {
      badge: 'border-blue-200 bg-blue-50 text-blue-800',
      ring: '#2563eb',
      panel: 'border-blue-100 bg-white',
      icon: 'bg-blue-100 text-blue-700',
      text: 'text-blue-700',
      surface: 'bg-blue-50 text-blue-800',
    };
  }

  if (level === SCORE_LEVELS.TRENDING) {
    return {
      badge: 'border-violet-200 bg-violet-50 text-violet-800',
      ring: '#8b5cf6',
      panel: 'border-violet-100 bg-white',
      icon: 'bg-violet-100 text-violet-700',
      text: 'text-violet-700',
      surface: 'bg-violet-50 text-violet-800',
    };
  }

  return {
    badge: 'border-amber-200 bg-amber-50 text-amber-800',
    ring: '#f59e0b',
    panel: 'border-amber-100 bg-white',
    icon: 'bg-amber-100 text-amber-700',
    text: 'text-amber-700',
    surface: 'bg-amber-50 text-amber-800',
  };
};

const buildEvidenceReasons = (evidenceSummary = {}) => {
  const reasons = [];
  const skillOverlap = Number(evidenceSummary.skill_overlap);
  const semanticStrength = normalizeText(evidenceSummary.semantic_strength).toUpperCase();

  if (Number.isFinite(skillOverlap) && skillOverlap > 0) {
    reasons.push(
      skillOverlap === 1
        ? '1 matching skill signal'
        : `${skillOverlap} matching skill signals`,
    );
  }
  if (evidenceSummary.role_match) reasons.push('Role alignment detected');
  if (evidenceSummary.title_overlap) reasons.push('Title language overlaps your goals');
  if (evidenceSummary.industry_match) reasons.push('Industry preference aligned');
  if (evidenceSummary.resume_signal) reasons.push('Resume signal detected');
  if (semanticStrength === 'STRONG') reasons.push('Semantic similarity is strong');

  return reasons;
};

const formatGapLabel = (gap) =>
  normalizeText(gap)
    .replace(/^missing\s+/i, '')
    .replace(/\s+experience$/i, '')
    .replace(/\s+skill$/i, '')
    .trim();

export const buildRecommendationViewModel = (recommendation, options = {}) => {
  if (!recommendation) return null;

  const scorePercent = getRecommendationScorePercent(
    recommendation.score ?? recommendation.match_score,
  );
  const scoreLabel = normalizeText(recommendation.score_label) || 'Recommended';
  const confidenceKey = normalizeText(recommendation.recommendation_confidence).toUpperCase();
  const isSparseProfile =
    normalizeText(recommendation.recommendation_mode).toUpperCase() === 'SPARSE_PROFILE' ||
    normalizeText(recommendation.profile_strength).toUpperCase() === 'LOW';
  const confidenceLabel = isSparseProfile
    ? 'Limited profile data'
    : CONFIDENCE_LABELS[confidenceKey] || 'Confidence improving';
  const tone = getRecommendationTone(recommendation);
  const rawReasons = normalizeArray(recommendation.reasons || recommendation.reason);
  const evidenceReasons = buildEvidenceReasons(recommendation.evidence_summary);
  const visibleReasons = dedupe([...rawReasons, ...evidenceReasons]).slice(0, options.reasonLimit || 4);
  const gaps = normalizeArray(recommendation.gaps).map(formatGapLabel).filter(Boolean);
  const fitLabel =
    scorePercent >= 80
      ? 'Strong match'
      : scorePercent >= 60
        ? 'Good fit'
        : scorePercent > 0
          ? 'Worth a look'
          : scoreLabel;
  const scoreText =
    scorePercent && scorePercent > 0 ? `${scorePercent}% match` : scoreLabel;

  return {
    scorePercent,
    scoreLabel,
    fitLabel,
    scoreText,
    confidenceLabel,
    visibleReasons,
    gaps: dedupe(gaps).slice(0, options.gapLimit || 4),
    hasGaps: gaps.length > 0,
    tone,
    isSparseProfile,
  };
};

export const mergeRecommendationIntoOpportunity = (opportunity, recommendation) => {
  if (!opportunity || !recommendation) return opportunity;

  return {
    ...opportunity,
    recommendation,
    score: recommendation.score,
    match_score: recommendation.match_score ?? recommendation.score,
    score_label: recommendation.score_label,
    score_level: recommendation.score_level,
    reasons: recommendation.reasons,
    reason: recommendation.reason,
    gaps: recommendation.gaps,
    recommendation_confidence: recommendation.recommendation_confidence,
    recommendation_mode: recommendation.recommendation_mode,
    profile_strength: recommendation.profile_strength,
    evidence_summary: recommendation.evidence_summary,
  };
};

export const hasActiveResume = (user) => Boolean(user?.profil?.active_resume);

export const getProfileCompletionScore = (user) => {
  const score = Number(user?.profil?.profile_completion?.score);
  return Number.isFinite(score) ? Math.max(0, Math.min(score, 100)) : 0;
};

export const getProfileRecommendationTier = (user) => {
  const score = getProfileCompletionScore(user);
  if (score < FOR_YOU_PROFILE_MIN_SCORE) return 'insufficient';
  if (score <= FOR_YOU_PROFILE_FULL_SCORE) return 'partial';
  return 'complete';
};

export const canUseForYouFeed = (user) =>
  getProfileCompletionScore(user) >= FOR_YOU_PROFILE_MIN_SCORE;

export const isFallbackRecommendation = (recommendation) => {
  const mode = normalizeText(recommendation?.recommendation_mode).toUpperCase();
  const label = normalizeText(recommendation?.score_label).toLowerCase();

  return mode === 'FALLBACK' || label === 'recent';
};

export const isQualifiedRecommendation = (recommendation, minScore = FOR_YOU_MIN_MATCH_SCORE) => {
  if (!recommendation || isFallbackRecommendation(recommendation)) return false;

  const scorePercent = getRecommendationScorePercent(
    recommendation.score ?? recommendation.match_score,
  );

  return scorePercent !== null && scorePercent >= minScore;
};

export const isProfileIncomplete = (user) => {
  const profile = user?.profil;
  if (!profile) return false;

  const missing = Array.isArray(profile.profile_completion?.missing)
    ? profile.profile_completion.missing
    : [];
  const skills = Array.isArray(profile.competences) ? profile.competences : [];
  const targetRoles = Array.isArray(profile.target_roles) ? profile.target_roles : [];

  return (
    getProfileCompletionScore(user) < 80 ||
    missing.length > 0 ||
    skills.length === 0 ||
    targetRoles.length === 0 ||
    !hasActiveResume(user)
  );
};

export const getProfileActionItems = (user) => {
  const profile = user?.profil || {};
  const actions = [];

  if (!hasActiveResume(user)) actions.push('Upload Resume');
  if (!Array.isArray(profile.competences) || profile.competences.length === 0) actions.push('Add Skills');
  if (!Array.isArray(profile.target_roles) || profile.target_roles.length === 0) {
    actions.push('Add Preferred Roles');
  }

  return actions.length ? actions : ['Review Profile'];
};
