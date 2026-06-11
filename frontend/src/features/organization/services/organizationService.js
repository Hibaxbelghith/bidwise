import api from '../../../lib/api.js';
import { buildOrganizationProfilePayload } from '../organizationFlow.js';

const firstMessage = (value) => {
  if (Array.isArray(value)) return value[0];
  if (typeof value === 'string') return value;
  return null;
};

const formatRetryDelay = (seconds) => {
  const value = Number(seconds || 0);
  if (!Number.isFinite(value) || value <= 0) return '';
  const minutes = Math.ceil(value / 60);
  if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''}`;
  const hours = Math.ceil(minutes / 60);
  return `${hours} hour${hours > 1 ? 's' : ''}`;
};

export const parseOrganizationApiError = (error) => {
  const data = error?.response?.data;
  const fallback = error?.message || 'Unable to save organization profile.';
  const status = error?.response?.status;

  if (status === 429) {
    const retryAfter = formatRetryDelay(data?.available_in || error?.response?.headers?.['retry-after']);
    return {
      message: retryAfter
        ? `Publishing limit reached. You can publish up to 5 opportunities per hour. Please try again in about ${retryAfter}.`
        : 'Publishing limit reached. You can publish up to 5 opportunities per hour. Please try again later.',
      fields: {},
      code: 'rate_limited',
    };
  }

  if (!data || typeof data !== 'object') {
    return { message: fallback, fields: {} };
  }

  const fields = {};
  Object.entries(data).forEach(([key, value]) => {
    const message = firstMessage(value);
    if (message) fields[key] = message;
  });

  const securityMessage = firstMessage(data.turnstile_token);
  const firstFieldMessage = Object.values(fields)[0];
  return {
    message:
      data.detail ||
      data.error ||
      firstMessage(data.non_field_errors) ||
      securityMessage ||
      firstFieldMessage ||
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

export const listOrganizationOpportunities = async () => {
  const response = await api.get('/organization/opportunities/');
  return Array.isArray(response.data) ? response.data : [];
};

export const getOrganizationOpportunity = async (opportunityId, { signal } = {}) => {
  const response = await api.get(`/organization/opportunities/${opportunityId}/`, { signal });
  return response.data;
};

export const createOrganizationOpportunity = async (values) => {
  const response = await api.post('/organization/opportunities/', values);
  return response.data;
};

export const updateOrganizationOpportunity = async (opportunityId, values) => {
  const { type: _immutableType, ...editableValues } = values;
  const response = await api.patch(`/organization/opportunities/${opportunityId}/`, editableValues);
  return response.data;
};

export const changeOrganizationOpportunityStatus = async (opportunityId, action) => {
  const response = await api.post(`/organization/opportunities/${opportunityId}/${action}/`);
  return response.data;
};

export const uploadOrganizationTenderDocument = async ({ file, type, label }) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('type', type || 'autres');
  formData.append('label', label || '');

  const response = await api.post('/organization/opportunities/tender-documents/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const getOpportunityApplications = async (opportunityId) => {
  const response = await api.get(`/organization/opportunities/${opportunityId}/applications/`);
  return Array.isArray(response.data) ? response.data : [];
};

export const getOpportunitiesApplicationsStats = async (opportunities) => {
  const stats = {};
  
  const fetchApplications = async (opportunity) => {
    try {
      const applications = await getOpportunityApplications(opportunity.id);
      stats[opportunity.id] = applications;
    } catch (error) {
      // If error fetching applications, set empty array
      stats[opportunity.id] = [];
    }
  };

  // Fetch all applications in parallel
  await Promise.all(opportunities.map(fetchApplications));
  
  return stats;
};

export const listAllOrganizationApplications = async () => {
  const response = await api.get('/organization/applications/');
  return Array.isArray(response.data) ? response.data : [];
};

export const getCandidateApplicationProfile = async (applicationId) => {
  const response = await api.get(
    `/organization/applications/${applicationId}/candidate-profile/`
  );
  return response.data;
};

export const rejectApplication = async (opportunityId, applicationId, options = {}) => {
  const response = await api.patch(
    `/organization/opportunities/${opportunityId}/applications/${applicationId}/reject/`,
    options.restoreStatus ? { restore_status: options.restoreStatus } : {}
  );
  return response.data;
};

export const acceptApplication = async (opportunityId, applicationId, options = {}) => {
  const response = await api.patch(
    `/organization/opportunities/${opportunityId}/applications/${applicationId}/accept/`,
    options.restoreStatus ? { restore_status: options.restoreStatus } : {}
  );
  return response.data;
};

export const deleteApplication = async (opportunityId, applicationId) => {
  const response = await api.delete(
    `/organization/opportunities/${opportunityId}/applications/${applicationId}/`
  );
  return response.data;
};
