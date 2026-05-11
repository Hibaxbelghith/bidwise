import api from '../../../lib/api.js';
import { buildOrganizationProfilePayload } from '../organizationFlow.js';

const firstMessage = (value) => {
  if (Array.isArray(value)) return value[0];
  if (typeof value === 'string') return value;
  return null;
};

export const parseOrganizationApiError = (error) => {
  const data = error?.response?.data;
  const fallback = error?.message || 'Unable to save organization profile.';

  if (!data || typeof data !== 'object') {
    return { message: fallback, fields: {} };
  }

  const fields = {};
  Object.entries(data).forEach(([key, value]) => {
    const message = firstMessage(value);
    if (message) fields[key] = message;
  });

  return {
    message:
      data.detail ||
      data.error ||
      firstMessage(data.non_field_errors) ||
      fallback,
    fields,
  };
};

export const getOrganizationProfile = async () => {
  const response = await api.get('/profile/organization/');
  return response.data;
};

export const upsertOrganizationProfile = async (values) => {
  const response = await api.put('/profile/organization/', buildOrganizationProfilePayload(values));
  return response.data;
};
