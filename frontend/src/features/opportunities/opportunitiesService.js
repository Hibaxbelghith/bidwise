import api from '../../lib/api';

const OPPORTUNITIES_ENDPOINT = '/opportunities/';
const LEGACY_OPPORTUNITIES_ENDPOINT = '/opportunites/';

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

  try {
    const response = await api.get(OPPORTUNITIES_ENDPOINT, { params });
    return response.data;
  } catch (error) {
    if (error?.response?.status === 404) {
      const fallbackResponse = await api.get(LEGACY_OPPORTUNITIES_ENDPOINT, { params });
      return fallbackResponse.data;
    }
    throw error;
  }
};

export const getOpportunityById = async (id) => {
  if (!id) {
    throw new Error('Opportunity id is required');
  }

  try {
    const response = await api.get(`${OPPORTUNITIES_ENDPOINT}${id}/`);
    return response.data;
  } catch (error) {
    if (error?.response?.status === 404) {
      const fallbackResponse = await api.get(`${LEGACY_OPPORTUNITIES_ENDPOINT}${id}/`);
      return fallbackResponse.data;
    }
    throw error;
  }
};

export const getSimilarOpportunities = async (id, k = 5) => {
  if (!id) return [];

  const safeK = Math.max(1, Math.min(Number(k) || 5, 50));

  try {
    const response = await api.get(`${OPPORTUNITIES_ENDPOINT}${id}/similar/`, {
      params: { k: safeK },
    });
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    if (error?.response?.status === 404) {
      const fallbackResponse = await api.get(`${LEGACY_OPPORTUNITIES_ENDPOINT}${id}/similar/`, {
        params: { k: safeK },
      });
      return Array.isArray(fallbackResponse.data) ? fallbackResponse.data : [];
    }
    throw error;
  }
};
