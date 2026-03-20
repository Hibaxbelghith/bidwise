import api from '../../lib/api';

const OPPORTUNITIES_ENDPOINT = '/opportunities/';
const LEGACY_OPPORTUNITIES_ENDPOINT = '/opportunites/';

export const listOpportunities = async ({
  search = '',
  type = '',
  status = '',
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
