import api from '../../../lib/api';

const OPPORTUNITIES_ENDPOINT = '/opportunities/';
const LEGACY_OPPORTUNITIES_ENDPOINT = '/opportunites/';
const RECOMMENDATIONS_ENDPOINT = '/recommendations/';
const TENDER_RECOMMENDATIONS_ENDPOINT = '/opportunities/tenders/recommendations/';

const normalizeString = (value) => String(value || '').trim();
const normalizeArray = (value) => (Array.isArray(value) ? value.filter(Boolean) : []);
const normalizeObject = (value) =>
  value && typeof value === 'object' && !Array.isArray(value) ? value : {};
const normalizeNumberOrNull = (value) => {
  if (value === null || value === undefined || value === '') return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const normalizeTenderPriorityLabel = (priority) => {
  const normalized = normalizeString(priority).toLowerCase();
  if (!normalized) return '';

  if (normalized.includes('forte') || normalized.includes('strong')) {
    return 'Strong priority';
  }
  if (normalized.includes('surveiller') || normalized.includes('watch')) {
    return 'Watch closely';
  }
  if (normalized.includes('faible') || normalized.includes('low')) {
    return 'Low priority';
  }
  if (normalized.includes('veille') || normalized.includes('general')) {
    return 'General watch';
  }

  return normalizeString(priority);
};

export const normalizeRecommendation = (recommendation) => {
  const raw = normalizeObject(recommendation);
  const reasons = normalizeArray(raw.reasons || raw.reason);

  return {
    ...raw,
    id: raw.id ?? null,
    title: normalizeString(raw.title),
    score: normalizeNumberOrNull(raw.score),
    match_score: normalizeNumberOrNull(raw.match_score ?? raw.score),
    semantic_score: normalizeNumberOrNull(raw.semantic_score),
    business_score: normalizeNumberOrNull(raw.business_score),
    feedback_score: normalizeNumberOrNull(raw.feedback_score),
    score_label: normalizeString(raw.score_label),
    score_level: normalizeString(raw.score_level),
    reason: reasons,
    reasons,
    gaps: normalizeArray(raw.gaps),
    recommendation_confidence: normalizeString(raw.recommendation_confidence),
    profile_strength: normalizeString(raw.profile_strength),
    recommendation_mode: normalizeString(raw.recommendation_mode),
    recommendation_bucket: normalizeString(raw.recommendation_bucket),
    recommendation_bucket_reason: normalizeString(raw.recommendation_bucket_reason),
    evidence_summary: normalizeObject(raw.evidence_summary),
    location: normalizeString(raw.location),
    company: normalizeString(raw.company),
    type: normalizeString(raw.type),
  };
};

const isPublicFilterSource = (source) => {
  const name = normalizeString(source?.nom).toLowerCase();
  if (!name) return false;
  return !(
    name.includes('bidwise recommendation') ||
    name.includes('bidwise recommendations') ||
    name.includes('bidwise_recommendation')
  );
};

export const normalizeOpportunity = (opportunity) => {
  const raw = normalizeObject(opportunity);

  return {
    ...raw,
    id: raw.id ?? null,
    titre: normalizeString(raw.titre),
    description: String(raw.description || ''),
    description_html: String(raw.description_html || ''),
    organisation_nom: normalizeString(raw.organisation_nom),
    organisation_logo: normalizeString(raw.organisation_logo),
    company_logo: normalizeString(raw.company_logo),
    logo_url: normalizeString(raw.logo_url),
    ville: normalizeString(raw.ville),
    salary: String(raw.salary || ''),
    type_opportunite: normalizeString(raw.type_opportunite),
    statut: normalizeString(raw.statut),
    quality_score: normalizeNumberOrNull(raw.quality_score),
    date_publication: raw.date_publication || '',
    date_limite: raw.date_limite || '',
    date_creation: raw.date_creation || '',
    contract_type: normalizeString(raw.contract_type),
    availability: normalizeString(raw.availability),
    normalized_work_mode: normalizeString(raw.normalized_work_mode),
    education_level: normalizeString(raw.education_level),
    source_item_url: normalizeString(raw.source_item_url),
    source: normalizeObject(raw.source),
    skills: normalizeArray(raw.skills),
    languages: normalizeArray(raw.languages),
    languages_fallback: normalizeArray(raw.languages_fallback),
    experience: normalizeObject(raw.experience),
    extra_data: normalizeObject(raw.extra_data),
    similarity_score: normalizeNumberOrNull(raw.similarity_score),
    score: normalizeNumberOrNull(raw.score),
    match_score: normalizeNumberOrNull(raw.match_score ?? raw.score),
    semantic_score: normalizeNumberOrNull(raw.semantic_score),
    business_score: normalizeNumberOrNull(raw.business_score),
    feedback_score: normalizeNumberOrNull(raw.feedback_score),
    score_label: normalizeString(raw.score_label),
    score_level: normalizeString(raw.score_level),
    reason: normalizeArray(raw.reason || raw.reasons),
    reasons: normalizeArray(raw.reasons || raw.reason),
    gaps: normalizeArray(raw.gaps),
    recommendation_confidence: normalizeString(raw.recommendation_confidence),
    profile_strength: normalizeString(raw.profile_strength),
    recommendation_mode: normalizeString(raw.recommendation_mode),
    recommendation_bucket: normalizeString(raw.recommendation_bucket),
    recommendation_bucket_reason: normalizeString(raw.recommendation_bucket_reason),
    evidence_summary: normalizeObject(raw.evidence_summary),
    recommendation: raw.recommendation ? normalizeRecommendation(raw.recommendation) : null,
    accepts_direct_applications: Boolean(raw.accepts_direct_applications),
    my_application: raw.my_application ? normalizeObject(raw.my_application) : null,
  };
};

const normalizeTenderRecommendationResult = (item) => {
  const raw = normalizeObject(item);
  const opportunity = normalizeOpportunity(raw.opportunity);
  const score = normalizeNumberOrNull(raw.score);
  const rawPriority = normalizeString(raw.priority);
  const priority = normalizeTenderPriorityLabel(rawPriority);
  const reasons = normalizeArray(raw.reasons);
  const components = normalizeObject(raw.components);

  return {
    ...opportunity,
    tender_recommendation: {
      score,
      priority,
      raw_priority: rawPriority,
      reasons,
      components,
    },
    recommendation:
      score === null
        ? null
        : normalizeRecommendation({
            id: opportunity.id,
            title: opportunity.titre,
            company: opportunity.organisation_nom,
            location: opportunity.ville,
            type: opportunity.type_opportunite,
            score,
            match_score: score,
            score_label: priority,
            score_level: priority.toLowerCase().includes('strong')
              ? 'HIGH'
              : priority.toLowerCase().includes('watch')
                ? 'MEDIUM'
                : 'LOW',
            recommendation_mode: 'TENDER_WATCH',
            recommendation_confidence: priority,
            recommendation_bucket: priority.toLowerCase().includes('strong')
              ? 'STRONG_MATCH'
              : 'RELATED_REVIEW',
            recommendation_bucket_reason: priority,
            reasons,
            evidence_summary: {
              semantic_strength: components?.semantic >= 0.65 ? 'STRONG' : 'MEDIUM',
              skill_overlap: 0,
              profile_skill_overlap: 0,
              role_match: false,
              title_overlap: false,
              industry_match: Number(components?.category) >= 0.7,
              llm_family_match: Number(components?.category) > 0,
              resume_signal: false,
            },
          }),
  };
};

const normalizePaginatedResponse = (payload) => {
  const raw = normalizeObject(payload);

  return {
    ...raw,
    count: Number(raw.count) || 0,
    next: raw.next ?? null,
    previous: raw.previous ?? null,
    facets: normalizeObject(raw.facets),
    results: normalizeArray(raw.results).map(normalizeOpportunity),
  };
};

const getWithLegacyFallback = async (path, legacyPath, config) => {
  try {
    const response = await api.get(path, config);
    return response.data;
  } catch (error) {
    if (error?.response?.status === 404) {
      const fallbackResponse = await api.get(legacyPath, config);
      return fallbackResponse.data;
    }

    throw error;
  }
};

export const listOpportunities = async ({
  search = '',
  type = '',
  status = '',
  city = '',
  source = '',
  workMode = '',
  experienceLevel = '',
  datePosted = '',
  deadlineWindow = '',
  sort = 'quality',
  ordering = '',
  sourceCap = 0,
  diversifySources = true,
  page = 1,
  pageSize = 20,
} = {}) => {
  const params = {
    page,
    page_size: pageSize,
  };

  if (search) params.search = search;
  if (type) params.type_opportunite = type;
  if (status) params.statut = status;
  if (city && String(city).trim()) params.ville = String(city).trim();
  if (source) params.source = source;
  if (workMode) params.work_mode = workMode;
  if (experienceLevel) params.experience_level = experienceLevel;
  if (datePosted) params.date_posted = datePosted;
  if (deadlineWindow) params.deadline_window = deadlineWindow;
  if (ordering) {
    params.ordering = ordering;
  } else if (sort) {
    params.sort = sort;
  }
  if (sourceCap) params.source_cap = sourceCap;
  if (!diversifySources) params.diversify_sources = 0;

  const data = await getWithLegacyFallback(OPPORTUNITIES_ENDPOINT, LEGACY_OPPORTUNITIES_ENDPOINT, {
    params,
  });
  return normalizePaginatedResponse(data);
};

export const listOpportunitySources = async () => {
  const response = await api.get('/sources/');
  return normalizeArray(response.data?.results || response.data)
    .map((source) => ({
      id: source?.id ?? null,
      nom: normalizeString(source?.nom),
      url: normalizeString(source?.url),
      type_source: normalizeString(source?.type_source),
    }))
    .filter((source) => source.id !== null && isPublicFilterSource(source));
};

export const listOpportunityRecommendations = async ({ limit = 20 } = {}) => {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 20, 50));
  const response = await api.get(RECOMMENDATIONS_ENDPOINT, {
    params: { limit: safeLimit },
  });
  return normalizeArray(response.data).map(normalizeRecommendation);
};

export const listTenderRecommendations = async ({ limit = 50 } = {}) => {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 50, 50));
  const response = await api.get(TENDER_RECOMMENDATIONS_ENDPOINT, {
    params: { limit: safeLimit },
  });
  const raw = normalizeObject(response.data);

  return {
    count: Number(raw.count) || 0,
    next: null,
    previous: null,
    facets: {},
    results: normalizeArray(raw.results).map(normalizeTenderRecommendationResult),
  };
};

export const listTrendingOpportunities = async ({ limit = 8 } = {}) =>
  listOpportunities({
    ordering: '-quality_score',
    pageSize: limit,
    sourceCap: 2,
  }).then((payload) => payload.results);

export const listRecentOpportunities = async ({ limit = 8 } = {}) =>
  listOpportunities({
    ordering: '-date_publication',
    pageSize: limit,
    diversifySources: false,
  }).then((payload) => payload.results);

export const listLocationOpportunities = async ({ location, limit = 6 } = {}) => {
  const city = String(location || '').trim();
  if (!city) return [];

  return listOpportunities({
    city,
    ordering: '-date_publication',
    pageSize: limit,
  }).then((payload) => payload.results);
};

export const getOpportunityById = async (id) => {
  if (!id) {
    throw new Error('Opportunity id is required');
  }

  const data = await getWithLegacyFallback(
    `${OPPORTUNITIES_ENDPOINT}${id}/`,
    `${LEGACY_OPPORTUNITIES_ENDPOINT}${id}/`,
  );
  return normalizeOpportunity(data);
};

export const getSimilarOpportunities = async (id, k = 5) => {
  if (!id) return [];

  const safeK = Math.max(1, Math.min(Number(k) || 5, 50));

  const data = await getWithLegacyFallback(
    `${OPPORTUNITIES_ENDPOINT}${id}/similar/`,
    `${LEGACY_OPPORTUNITIES_ENDPOINT}${id}/similar/`,
    { params: { k: safeK } },
  );
  return normalizeArray(data).map(normalizeOpportunity);
};

export const getResumeMatch = async (opportunityId) => {
  if (!opportunityId) {
    throw new Error('Opportunity id is required');
  }

  const response = await api.get(`${OPPORTUNITIES_ENDPOINT}${opportunityId}/resume-match/`);
  return normalizeObject(response.data);
};

export const generateResumeMatchAnalysis = async (opportunityId) => {
  if (!opportunityId) {
    throw new Error('Opportunity id is required');
  }

  const response = await api.post(`${OPPORTUNITIES_ENDPOINT}${opportunityId}/resume-match/actions/`, {
    action: 'full_fit_analysis',
  });
  return normalizeObject(response.data);
};

export const generateResumeMatchAction = async (opportunityId, action) => {
  if (!opportunityId) {
    throw new Error('Opportunity id is required');
  }
  if (!action) {
    throw new Error('Resume match action is required');
  }

  const response = await api.post(`${OPPORTUNITIES_ENDPOINT}${opportunityId}/resume-match/actions/`, {
    action,
  });
  return normalizeObject(response.data);
};

export const askOpportunityAssistant = async (opportunityId, question, history = [], recommendation = null) => {
  if (!opportunityId) {
    throw new Error('Opportunity id is required');
  }

  const normalizedQuestion = String(question || '').trim();
  if (!normalizedQuestion) {
    throw new Error('A question is required');
  }
  if (normalizedQuestion.length > 500) {
    throw new Error('Question must be at most 500 characters');
  }

  const normalizedHistory = Array.isArray(history)
    ? history
        .slice(-4)
        .filter(
          (message) =>
            message &&
            ['user', 'assistant'].includes(message.role) &&
            String(message.content || '').trim(),
        )
        .map((message) => ({
          role: message.role,
          content: String(message.content).trim().slice(0, 1800),
        }))
    : [];

  const payload = {
    question: normalizedQuestion,
    history: normalizedHistory,
  };

  if (recommendation && typeof recommendation === 'object' && !Array.isArray(recommendation)) {
    payload.recommendation = normalizeRecommendation(recommendation);
  }

  const response = await api.post(`${OPPORTUNITIES_ENDPOINT}${opportunityId}/assistant/questions/`, payload);
  return normalizeObject(response.data);
};

export const downloadOptimizedAtsCv = async (opportunityId, optimizationMarkdown) => {
  if (!opportunityId) {
    throw new Error('Opportunity id is required');
  }
  const markdown = String(optimizationMarkdown || '').trim();
  if (!markdown) {
    throw new Error('Optimized CV content is required');
  }

  const response = await api.post(
    `${OPPORTUNITIES_ENDPOINT}${opportunityId}/resume-match/export-ats-cv/`,
    { optimization_markdown: markdown },
    { responseType: 'blob' },
  );
  const disposition = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return {
    blob: response.data,
    filename: match?.[1] || 'optimized_ats_cv.docx',
  };
};

export const downloadCoverLetterDocx = async (opportunityId, coverLetterMarkdown) => {
  if (!opportunityId) {
    throw new Error('Opportunity id is required');
  }
  const markdown = String(coverLetterMarkdown || '').trim();
  if (!markdown) {
    throw new Error('Cover letter content is required');
  }

  const response = await api.post(
    `${OPPORTUNITIES_ENDPOINT}${opportunityId}/resume-match/export-cover-letter/`,
    { cover_letter_markdown: markdown },
    { responseType: 'blob' },
  );
  const disposition = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return {
    blob: response.data,
    filename: match?.[1] || 'cover_letter.docx',
  };
};

export const uploadProfileResume = async (file, { activate = false } = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('activate', activate ? 'true' : 'false');

  const response = await api.post('/profile/resume/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return normalizeObject(response.data);
};

export const uploadApplicationCoverLetter = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/applications/cover-letter-upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return normalizeObject(response.data);
};

export const submitOrganizationApplication = async (opportunityId, payload) => {
  const response = await api.post(`/opportunities/${opportunityId}/apply/`, payload);
  return normalizeObject(response.data);
};

export const registerExternalApplicationClick = async (opportunityId) => {
  if (!opportunityId) {
    throw new Error('Opportunity id is required');
  }

  const response = await api.post(`/opportunities/${opportunityId}/external-apply-click/`, {});
  return normalizeObject(response.data);
};

export const updateExternalApplicationStatus = async (applicationId, statusValue) => {
  if (!applicationId) {
    throw new Error('Application id is required');
  }
  if (!statusValue) {
    throw new Error('External application status is required');
  }

  const response = await api.patch(`/me/applications/${applicationId}/external-status/`, {
    status: statusValue,
  });
  return normalizeObject(response.data);
};

export const confirmProfileResume = async (resumeId) => {
  const response = await api.patch('/profile/resume/', { resume_id: resumeId });
  return normalizeObject(response.data);
};

export const deleteProfileResume = async (resumeId) => {
  const suffix = resumeId ? `?resume_id=${encodeURIComponent(resumeId)}` : '';
  const response = await api.delete(`/profile/resume/${suffix}`);
  return normalizeObject(response.data);
};
