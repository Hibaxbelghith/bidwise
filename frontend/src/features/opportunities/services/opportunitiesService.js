import api from '../../../lib/api';

const OPPORTUNITIES_ENDPOINT = '/opportunities/';
const LEGACY_OPPORTUNITIES_ENDPOINT = '/opportunites/';

const normalizeString = (value) => String(value || '').trim();
const normalizeArray = (value) => (Array.isArray(value) ? value.filter(Boolean) : []);
const normalizeObject = (value) =>
  value && typeof value === 'object' && !Array.isArray(value) ? value : {};
const normalizeNumberOrNull = (value) => {
  if (value === null || value === undefined || value === '') return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const normalizeOpportunity = (opportunity) => {
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
    date_publication: raw.date_publication || '',
    date_limite: raw.date_limite || '',
    contract_type: normalizeString(raw.contract_type),
    availability: normalizeString(raw.availability),
    education_level: normalizeString(raw.education_level),
    source_item_url: normalizeString(raw.source_item_url),
    source: normalizeObject(raw.source),
    skills: normalizeArray(raw.skills),
    languages: normalizeArray(raw.languages),
    languages_fallback: normalizeArray(raw.languages_fallback),
    experience: normalizeObject(raw.experience),
    extra_data: normalizeObject(raw.extra_data),
    similarity_score: normalizeNumberOrNull(raw.similarity_score),
  };
};

const normalizePaginatedResponse = (payload) => {
  const raw = normalizeObject(payload);

  return {
    ...raw,
    count: Number(raw.count) || 0,
    next: raw.next ?? null,
    previous: raw.previous ?? null,
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
  ordering = '-date_publication',
  page = 1,
  pageSize = 20,
} = {}) => {
  const params = {
    page,
    page_size: pageSize,
    ordering,
  };

  if (search) params.search = search;
  if (type) params.type_opportunite = type;
  if (status) params.statut = status;
  if (city && String(city).trim()) params.ville = String(city).trim();
  if (source) params.source = source;

  const data = await getWithLegacyFallback(OPPORTUNITIES_ENDPOINT, LEGACY_OPPORTUNITIES_ENDPOINT, {
    params,
  });
  return normalizePaginatedResponse(data);
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
