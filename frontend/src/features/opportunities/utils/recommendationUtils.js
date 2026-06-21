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

const hasProfileListValues = (value) => normalizeArray(value).length > 0;

const hasExperienceSignal = (profile = {}) => {
  const level = normalizeText(profile?.niveau_experience);
  const years = Number(profile?.annees_experience);

  return Boolean(level) || (Number.isFinite(years) && years >= 0);
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

const reasonPriority = (reason) => {
  const text = normalizeText(reason).toLowerCase();
  if (text.includes('role aligned') || text.includes('role alignment')) return 10;
  if (text.includes('strong') && text.includes('alignment')) return 20;
  if (text.includes('matching skill') || text.includes('skill signal')) return 30;
  if (text.includes('job family') || text.includes('category')) return 40;
  if (text.includes('resume') || text.includes('semantic')) return 50;
  if (text.includes('remote') || text.includes('hybrid') || text.includes('on-site')) return 60;
  if (text.includes('location')) return 70;
  return 90;
};

const humanizeReason = (reason) => {
  const text = normalizeText(reason);
  if (!text) return '';
  if (text === 'Related job family signal detected') return 'Same job family as your profile';
  if (text === 'Role alignment detected') return 'Target role aligned';
  if (text === 'Title language overlaps your goals') return 'Title aligns with your goals';
  if (text === 'Industry preference aligned') return 'Industry preference aligned';
  if (text === 'Sector preference aligned') return 'Sector aligned with your profile';
  if (text === 'Resume signal detected') return 'CV signal detected';
  if (text === 'Semantic similarity is strong') return 'Strong profile similarity';
  if (text === 'On-site preference') return 'On-site preference aligned';
  return text;
};

const prioritizeReasons = (items, limit) =>
  dedupe(items.map(humanizeReason).filter(Boolean))
    .sort((left, right) => reasonPriority(left) - reasonPriority(right))
    .slice(0, limit);

const buildSignalChips = (recommendation = {}) => {
  const evidence = recommendation.evidence_summary || {};
  const rawReasons = normalizeArray(recommendation.reasons || recommendation.reason);
  const chips = [];
  const add = (key, label, tone = 'neutral') => {
    if (!chips.some((chip) => chip.key === key)) chips.push({ key, label, tone });
  };

  if (evidence.role_match) add('role', 'Role', 'strong');
  if (Number(evidence.skill_overlap) > 0 || Number(evidence.profile_skill_overlap) > 0) {
    add('skills', 'Skill match', 'strong');
  }
  if (evidence.llm_family_match) add('family', 'Job category', 'strong');
  if (evidence.resume_signal) add('cv', 'CV', 'support');
  if (rawReasons.some((reason) => /remote|hybrid|on-site|work preference/i.test(reason))) {
    add('work_mode', 'Work mode', 'support');
  }
  if (rawReasons.some((reason) => /location/i.test(reason))) add('location', 'Location', 'support');
  if (evidence.llm_family_mismatch) add('family_gap', 'Review category', 'gap');

  return chips.slice(0, 6);
};

export const getRecommendationScorePercent = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;

  const normalized = parsed > 1 ? parsed / 100 : parsed;
  return Math.round(Math.max(0, Math.min(normalized, 1)) * 100);
};

export const getRecommendationLevel = (recommendation) => {
  const scorePercent = getRecommendationScorePercent(
    recommendation?.score ?? recommendation?.match_score,
  );
  if (scorePercent === null) return SCORE_LEVELS.LOW;
  if (scorePercent <= 0 && normalizeText(recommendation?.score_label).toLowerCase() === 'recent') {
    return SCORE_LEVELS.TRENDING;
  }
  if (scorePercent >= 75) return SCORE_LEVELS.HIGH;
  if (scorePercent >= 45) return SCORE_LEVELS.MEDIUM;
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

  const isTenderRecommendation =
    normalizeText(recommendation.recommendation_mode).toUpperCase() === 'TENDER_WATCH';
  const scorePercent = getRecommendationScorePercent(
    recommendation.score ?? recommendation.match_score,
  );
  const scoreLabel = normalizeText(recommendation.score_label) || 'Recommended';
  const confidenceKey = normalizeText(recommendation.recommendation_confidence).toUpperCase();
  const isSparseProfile =
    normalizeText(recommendation.recommendation_mode).toUpperCase() === 'SPARSE_PROFILE' ||
    normalizeText(recommendation.profile_strength).toUpperCase() === 'LOW';
  const baseConfidenceLabel = isSparseProfile
    ? 'Limited profile data'
    : CONFIDENCE_LABELS[confidenceKey] || 'Confidence improving';
  const bucket = normalizeText(recommendation.recommendation_bucket).toUpperCase();
  const isStrongBucket = bucket === 'STRONG_MATCH';
  const tone = getRecommendationTone(recommendation);
  const rawReasons = normalizeArray(recommendation.reasons || recommendation.reason);
  const evidenceReasons = buildEvidenceReasons(recommendation.evidence_summary);
  const visibleReasons = prioritizeReasons(
    [...rawReasons, ...evidenceReasons],
    options.reasonLimit || 4,
  );
  const gaps = normalizeArray(recommendation.gaps).map(formatGapLabel).filter(Boolean);
  const tenderScoreLabel = ['Strong priority', 'Watch closely', 'Low priority', 'General watch'].includes(scoreLabel)
    ? scoreLabel
    : '';
  const fitLabel = isTenderRecommendation
    ? tenderScoreLabel || (
      scorePercent >= 60
        ? 'Strong priority'
        : scorePercent >= 40
          ? 'Watch closely'
          : scorePercent > 0
            ? 'Low priority'
            : scoreLabel
    )
    : scorePercent >= 80
      ? 'Strong match'
      : scorePercent >= 60
        ? 'Good fit'
      : scorePercent > 0
          ? 'Worth a look'
          : scoreLabel;
  const confidenceLabel = isTenderRecommendation
    ? fitLabel === 'Strong priority'
      ? 'High confidence'
      : fitLabel === 'Watch closely'
        ? 'Confidence improving'
        : baseConfidenceLabel
    : baseConfidenceLabel;
  const scoreText =
    scorePercent && scorePercent > 0
      ? isTenderRecommendation
        ? `${scorePercent}% priority`
        : `${scorePercent}% match`
      : scoreLabel;
  const signalChips = buildSignalChips(recommendation);
  const primaryReason = visibleReasons[0] || '';
  const bucketReason = normalizeText(recommendation.recommendation_bucket_reason).replace(/[.!?]+$/, '');
  const highScoreRelatedReason =
    bucket === 'RELATED_REVIEW' && scorePercent >= 75 && bucketReason
      ? bucketReason
      : '';
  const matchSummary = isTenderRecommendation
    ? primaryReason
      ? `${fitLabel}: ${primaryReason}.`
      : `${fitLabel} based on your tender preferences.`
    : options.context === 'detail'
      ? isStrongBucket && scorePercent >= 70 && primaryReason
        ? `Recommended to apply: ${primaryReason}.`
        : scorePercent >= 60 && primaryReason
          ? `Good fit, but review the details: ${primaryReason}.${highScoreRelatedReason ? ` ${highScoreRelatedReason}.` : ''}`
          : primaryReason
            ? `Worth reviewing before applying: ${primaryReason}.`
            : `${fitLabel} based on your profile signals.`
      : isStrongBucket && scorePercent >= 70 && primaryReason
        ? `${primaryReason}.`
        : scorePercent >= 60 && primaryReason
          ? `Good fit: ${primaryReason}.`
          : primaryReason
            ? `Worth reviewing: ${primaryReason}.`
            : `${fitLabel} based on your profile signals.`;
  const panelTitle = isTenderRecommendation
    ? 'Tender priority'
    : options.context === 'detail'
      ? 'Your fit'
      : 'Recommendation match';
  const verdictLabel = isTenderRecommendation
    ? fitLabel
    : isStrongBucket && scorePercent >= 70
      ? 'Recommended to apply'
      : scorePercent >= 60
        ? 'Good fit'
        : scorePercent > 0
          ? 'Worth reviewing'
          : scoreLabel;
  const verdictDescription = isTenderRecommendation
    ? 'This tender is ranked using your preferred regions, tender categories, and semantic similarity.'
    : isStrongBucket && scorePercent >= 70
      ? 'Your profile has strong evidence for this opportunity.'
      : scorePercent >= 60
        ? 'The opportunity is relevant, but review the gaps before applying.'
        : 'Review the details carefully before deciding.';
  const isRecommendedToApply = verdictLabel === 'Recommended to apply';

  return {
    scorePercent,
    scoreLabel,
    fitLabel,
    scoreText,
    confidenceLabel,
    visibleReasons,
    signalChips,
    matchSummary,
    panelTitle,
    verdictLabel,
    verdictDescription,
    reasonsTitle: isTenderRecommendation ? 'Why this priority' : 'Why this matches',
    reviewLabel: isTenderRecommendation
      ? 'Review before action'
      : isRecommendedToApply
        ? 'Details to confirm'
        : 'Review before applying',
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
    recommendation_bucket: recommendation.recommendation_bucket,
    recommendation_bucket_reason: recommendation.recommendation_bucket_reason,
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

export const getRecommendationImprovementHints = (user) => {
  const profile = user?.profil || {};
  const hints = [];

  if (!hasProfileListValues(profile.target_roles)) {
    hints.push({
      type: 'target_roles',
      priority: 100,
      title: 'Add preferred roles',
      message: 'To improve recommendation accuracy.',
      ctaLabel: 'Add preferred roles',
    });
  }

  if (!hasProfileListValues(profile.work_mode_preferences)) {
    hints.push({
      type: 'work_preferences',
      priority: 95,
      title: 'Add work preferences',
      message: 'To refine opportunity matching.',
      ctaLabel: 'Add work preferences',
    });
  }

  if (!hasProfileListValues(profile.employment_types)) {
    hints.push({
      type: 'employment_preferences',
      priority: 90,
      title: 'Add employment preferences',
      message: 'Add employment preferences to sharpen role matching.',
      ctaLabel: 'Add employment preferences',
    });
  }

  if (!hasProfileListValues(profile.competences)) {
    hints.push({
      type: 'skills',
      priority: 80,
      title: 'Add skills',
      message: 'To improve recommendation precision.',
      ctaLabel: 'Add skills',
    });
  }

  if (!hasExperienceSignal(profile)) {
    hints.push({
      type: 'experience',
      priority: 75,
      title: 'Add experience details',
      message: 'Add your experience level to improve fit and ranking quality.',
      ctaLabel: 'Add experience',
    });
  }

  if (!hasProfileListValues(profile.preferred_locations)) {
    hints.push({
      type: 'preferred_locations',
      priority: 70,
      title: 'Add preferred locations',
      message: 'Add preferred locations to tailor where opportunities appear.',
      ctaLabel: 'Add locations',
    });
  }

  if (!hasActiveResume(user)) {
    hints.push({
      type: 'resume',
      priority: 60,
      title: 'Upload a resume',
      message: 'Upload a resume to enrich AI matching with additional context.',
      ctaLabel: 'Upload resume',
    });
  }

  if (hints.length === 0) {
    hints.push({
      type: 'profile_review',
      priority: 0,
      title: 'Review your profile',
      message: 'Keep your roles, preferences, and experience current so recommendations stay aligned.',
      ctaLabel: 'Review profile',
    });
  }

  return hints.sort((left, right) => right.priority - left.priority).slice(0, 2);
};

export const getProfileActionItems = (user) => {
  return getRecommendationImprovementHints(user).map((hint) => hint.ctaLabel);
};
