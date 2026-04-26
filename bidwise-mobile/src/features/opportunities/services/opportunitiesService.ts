import api from '@/src/shared/services/api';

const OPPORTUNITIES_ENDPOINT = '/opportunities/';
const LEGACY_OPPORTUNITIES_ENDPOINT = '/opportunites/';

export interface OpportunitySource {
  id: number;
  nom: string;
  url?: string | null;
  type_source?: string | null;
}

export interface OpportunityExperience {
  min: number | null;
  max: number | null;
}

export interface OpportunityDocument {
  url?: string | null;
  type?: string | null;
  label?: string | null;
}

export interface OpportunityLot {
  lot?: string | null;
  objet?: string | null;
  quantite?: string | null;
  region?: string | null;
  caution?: string | null;
}

export interface OpportunityExtraData {
  company_sector?: string | null;
  company_size?: string | null;
  reference?: string | null;
  experience_text?: string | null;
  contract_types?: string[] | null;
  education_levels?: string[] | null;
  job_qualifications?: string | null;
  pdf_url?: string | null;
  cahier_des_charges_url?: string | null;
  documents?: OpportunityDocument[] | null;
  lots?: OpportunityLot[] | null;
  structured?: Record<string, unknown> | null;
  region?: string | null;
  region_execution?: string | null;
  procedure?: string | null;
  financement?: string | null;
  type_commande?: string | null;
  delai_validite?: string | null;
  caution?: string | null;
  has_pdf?: boolean | null;
}

export interface Opportunity {
  id: number;
  titre?: string | null;
  description?: string | null;
  description_html?: string | null;
  organisation_nom?: string | null;
  company_logo?: string | null;
  ville?: string | null;
  type_opportunite?: string | null;
  statut?: string | null;
  date_publication?: string | null;
  date_limite?: string | null;
  source_item_url?: string | null;
  contract_type?: string | null;
  education_level?: string | null;
  availability?: string | null;
  salary?: string | null;
  skills?: string[];
  languages?: string[] | null;
  languages_fallback?: string[] | null;
  source?: OpportunitySource | null;
  experience?: OpportunityExperience | null;
  extra_data?: OpportunityExtraData | null;
}

export interface SimilarOpportunity {
  id: number;
  titre?: string | null;
  organisation_nom?: string | null;
  similarity_score?: number | null;
}

export interface OpportunitiesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Opportunity[];
}

export interface OpportunitiesQueryParams {
  page?: number;
  pageSize?: number;
  search?: string;
  type?: string;
  status?: string;
  city?: string;
  minSalary?: number;
  source?: string;
  ordering?: string;
}

function isNotFoundError(error: unknown): boolean {
  return (error as { response?: { status?: number } })?.response?.status === 404;
}

function normalizePaginatedResponse(payload: unknown): OpportunitiesResponse {
  const data = (payload ?? {}) as Partial<OpportunitiesResponse>;

  return {
    count: Number(data.count ?? 0),
    next: typeof data.next === 'string' ? data.next : null,
    previous: typeof data.previous === 'string' ? data.previous : null,
    results: Array.isArray(data.results) ? data.results : [],
  };
}

function buildListParams(params: OpportunitiesQueryParams = {}) {
  const {
    page = 1,
    pageSize = 20,
    search = '',
    type = '',
    status = '',
    city = '',
    minSalary,
    source = '',
    ordering = '-date_publication',
  } = params;

  const queryParams: Record<string, string | number> = {
    page,
    page_size: pageSize,
    ordering,
  };

  if (search.trim()) queryParams.search = search.trim();
  if (type.trim()) {
    queryParams.type = type.trim();
    queryParams.type_opportunite = type.trim();
  }
  if (status.trim()) queryParams.statut = status.trim();
  if (city.trim()) {
    queryParams.city = city.trim();
    queryParams.ville = city.trim();
  }
  if (Number.isFinite(minSalary) && Number(minSalary) > 0) {
    queryParams.min_salary = Math.floor(Number(minSalary));
  }
  if (source.trim()) queryParams.source = source.trim();

  return queryParams;
}

export async function getOpportunities(params: OpportunitiesQueryParams = {}): Promise<OpportunitiesResponse> {
  const queryParams = buildListParams(params);

  try {
    const response = await api.get(OPPORTUNITIES_ENDPOINT, { params: queryParams });
    return normalizePaginatedResponse(response.data);
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error;
    }

    const fallbackResponse = await api.get(LEGACY_OPPORTUNITIES_ENDPOINT, { params: queryParams });
    return normalizePaginatedResponse(fallbackResponse.data);
  }
}

export async function getOpportunityById(id: number | string): Promise<Opportunity> {
  const safeId = String(id || '').trim();
  if (!safeId) {
    throw new Error('Opportunity id is required');
  }

  const parsedId = Number(safeId);
  if (!Number.isInteger(parsedId) || parsedId <= 0) {
    throw new Error('Opportunity id must be a positive integer');
  }

  const normalizedId = String(parsedId);

  try {
    const response = await api.get(`${OPPORTUNITIES_ENDPOINT}${normalizedId}/`);
    return response.data as Opportunity;
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error;
    }

    const fallbackResponse = await api.get(`${LEGACY_OPPORTUNITIES_ENDPOINT}${normalizedId}/`);
    return fallbackResponse.data as Opportunity;
  }
}

function normalizeSimilarPayload(payload: unknown): SimilarOpportunity[] {
  if (Array.isArray(payload)) {
    return payload as SimilarOpportunity[];
  }

  const wrapped = payload as { results?: unknown } | null;
  if (wrapped && Array.isArray(wrapped.results)) {
    return wrapped.results as SimilarOpportunity[];
  }

  return [];
}

export async function getSimilarOpportunities(
  id: number | string,
  k = 5,
): Promise<SimilarOpportunity[]> {
  const safeId = String(id || '').trim();
  if (!safeId) {
    return [];
  }

  const parsedId = Number(safeId);
  if (!Number.isInteger(parsedId) || parsedId <= 0) {
    return [];
  }

  const safeK = Math.max(1, Math.min(Number(k) || 5, 50));
  const normalizedId = String(parsedId);

  try {
    const response = await api.get(`${OPPORTUNITIES_ENDPOINT}${normalizedId}/similar/`, {
      params: { k: safeK },
    });
    return normalizeSimilarPayload(response.data);
  } catch (error) {
    if (!isNotFoundError(error)) {
      throw error;
    }

    const fallbackResponse = await api.get(`${LEGACY_OPPORTUNITIES_ENDPOINT}${normalizedId}/similar/`, {
      params: { k: safeK },
    });
    return normalizeSimilarPayload(fallbackResponse.data);
  }
}
