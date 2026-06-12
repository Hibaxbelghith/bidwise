import api from '@/src/shared/services/api';

const OPPORTUNITIES_ENDPOINT = '/opportunities/';
const RECOMMENDATIONS_ENDPOINT = '/recommendations/';

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

export interface OpportunityEvidenceSummary {
  skill_overlap?: number | null;
  profile_skill_overlap?: number | null;
  role_match?: boolean | null;
  title_overlap?: boolean | null;
  industry_match?: boolean | null;
  resume_signal?: boolean | null;
  semantic_strength?: string | null;
  llm_family_match?: boolean | null;
  llm_family_mismatch?: boolean | null;
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

export interface OpportunityMyApplication {
  id?: number | null;
  status?: string | null;
  submitted_at?: string | null;
}

export interface Opportunity {
  id: number;
  titre?: string | null;
  title?: string | null;
  description?: string | null;
  description_html?: string | null;
  organisation_nom?: string | null;
  company?: string | null;
  company_logo?: string | null;
  ville?: string | null;
  location?: string | null;
  type_opportunite?: string | null;
  type?: string | null;
  statut?: string | null;
  quality_score?: number | null;
  date_publication?: string | null;
  date_limite?: string | null;
  source_item_url?: string | null;
  contract_type?: string | null;
  education_level?: string | null;
  availability?: string | null;
  salary?: string | null;
  skills?: string[];
  raw_skills?: string[];
  normalized_skills?: string[];
  languages?: string[] | null;
  languages_fallback?: string[] | null;
  source?: OpportunitySource | null;
  experience?: OpportunityExperience | null;
  experience_min?: number | null;
  experience_max?: number | null;
  experience_years?: number | null;
  extra_data?: OpportunityExtraData | null;
  similarity_score?: number | null;
  score?: number | null;
  match_score?: number | null;
  semantic_score?: number | null;
  business_score?: number | null;
  feedback_score?: number | null;
  score_label?: string | null;
  score_level?: string | null;
  reason?: string[];
  reasons?: string[];
  gaps?: string[];
  recommendation_confidence?: string | null;
  profile_strength?: string | null;
  recommendation_mode?: string | null;
  recommendation_bucket?: string | null;
  recommendation_bucket_reason?: string | null;
  evidence_summary?: OpportunityEvidenceSummary | null;
  recommendation?: Recommendation | null;
  accepts_direct_applications?: boolean;
  my_application?: OpportunityMyApplication | null;
}

export interface Recommendation extends Opportunity {
  recommendation?: null;
}

export interface SimilarOpportunity extends Opportunity {
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

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  return value
    .map((item) => String(item || '').trim())
    .filter(Boolean);
}

function buildExperience(opportunity: Opportunity): OpportunityExperience | null {
  if (opportunity.experience) {
    return opportunity.experience;
  }

  if (opportunity.experience_min === undefined && opportunity.experience_max === undefined) {
    return null;
  }

  return {
    min: opportunity.experience_min ?? null,
    max: opportunity.experience_max ?? null,
  };
}

function applyOpportunityAliases(opportunity: Opportunity): Opportunity {
  const reasons = normalizeStringArray(opportunity.reasons ?? opportunity.reason);

  return {
    ...opportunity,
    titre: opportunity.titre ?? opportunity.title ?? '',
    title: opportunity.title ?? opportunity.titre ?? '',
    organisation_nom: opportunity.organisation_nom ?? opportunity.company ?? '',
    company: opportunity.company ?? opportunity.organisation_nom ?? '',
    ville: opportunity.ville ?? opportunity.location ?? '',
    location: opportunity.location ?? opportunity.ville ?? '',
    type_opportunite: opportunity.type_opportunite ?? opportunity.type ?? '',
    type: opportunity.type ?? opportunity.type_opportunite ?? '',
    match_score: opportunity.match_score ?? opportunity.score ?? null,
    experience: buildExperience(opportunity),
    reasons,
    reason: reasons,
    skills: opportunity.skills ?? [],
    raw_skills: opportunity.raw_skills ?? [],
    normalized_skills: opportunity.normalized_skills ?? [],
  };
}

export function normalizeRecommendation(recommendation: Recommendation): Recommendation {
  return {
    ...applyOpportunityAliases(recommendation),
    recommendation: null,
  };
}

export function normalizeOpportunity(opportunity: Opportunity): Opportunity {
  return {
    ...applyOpportunityAliases(opportunity),
    recommendation: opportunity.recommendation
      ? normalizeRecommendation(opportunity.recommendation)
      : null,
  };
}

function normalizePaginatedResponse(payload: Partial<OpportunitiesResponse> | null | undefined): OpportunitiesResponse {
  return {
    count: Number(payload?.count ?? 0),
    next: payload?.next ?? null,
    previous: payload?.previous ?? null,
    results: Array.isArray(payload?.results)
      ? payload.results.map((item) => normalizeOpportunity(item as Opportunity))
      : [],
  };
}

function normalizeSimilarPayload(payload: unknown): SimilarOpportunity[] {
  if (Array.isArray(payload)) {
    return payload.map((item) => normalizeOpportunity(item as Opportunity) as SimilarOpportunity);
  }

  if (payload && typeof payload === 'object' && Array.isArray((payload as { results?: unknown[] }).results)) {
    return (payload as { results: unknown[] }).results.map(
      (item) => normalizeOpportunity(item as Opportunity) as SimilarOpportunity,
    );
  }

  return [];
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
    ordering = '-quality_score',
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
  const response = await api.get(OPPORTUNITIES_ENDPOINT, {
    params: buildListParams(params),
  });

  return normalizePaginatedResponse(response.data as Partial<OpportunitiesResponse>);
}

export async function listOpportunityRecommendations({
  limit = 20,
}: {
  limit?: number;
} = {}): Promise<Recommendation[]> {
  const safeLimit = Math.max(1, Math.min(Number(limit) || 20, 50));
  const response = await api.get(RECOMMENDATIONS_ENDPOINT, {
    params: { limit: safeLimit },
  });

  return Array.isArray(response.data)
    ? response.data.map((item) => normalizeRecommendation(item as Recommendation))
    : [];
}

export async function getOpportunityById(id: number | string): Promise<Opportunity> {
  const parsedId = Number(String(id || '').trim());
  if (!Number.isInteger(parsedId) || parsedId <= 0) {
    throw new Error('Opportunity id must be a positive integer');
  }

  const response = await api.get(`${OPPORTUNITIES_ENDPOINT}${parsedId}/`);
  return normalizeOpportunity(response.data as Opportunity);
}

export async function getSimilarOpportunities(
  id: number | string,
  k = 5,
): Promise<SimilarOpportunity[]> {
  const parsedId = Number(String(id || '').trim());
  if (!Number.isInteger(parsedId) || parsedId <= 0) {
    return [];
  }

  const safeK = Math.max(1, Math.min(Number(k) || 5, 50));
  const response = await api.get(`${OPPORTUNITIES_ENDPOINT}${parsedId}/similar/`, {
    params: { k: safeK },
  });

  return normalizeSimilarPayload(response.data);
}
