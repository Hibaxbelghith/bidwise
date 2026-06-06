import adminApi from '../../../lib/adminApi.js';

export const getDashboard = ({ view } = {}) => {
  const params = {};
  if (view) params.view = view;

  return adminApi.get('/admin/dashboard/', { params });
};

export const getOpportunities = ({ page, search, source, signal } = {}) => {
  const params = { page };
  if (search) params.search = search;
  if (source) params.source = Number(source);

  return adminApi.get('/admin/opportunities/', {
    params,
    signal,
  });
};

export const getSources = ({ signal } = {}) => adminApi.get('/sources/', { signal });

export const deleteOpportunity = (id) => adminApi.delete(`/admin/opportunities/${id}/`);

export const approveOrganizationOpportunity = (id, note = '') => (
  adminApi.post(`/admin/organization-opportunities/${id}/approve/`, { note })
);

export const rejectOrganizationOpportunity = (id, note = '') => (
  adminApi.post(`/admin/organization-opportunities/${id}/reject/`, { note })
);

export const fetchAdminDashboard = getDashboard;
export const fetchAdminOpportunities = getOpportunities;
export const fetchAdminSources = getSources;
export const deleteAdminOpportunity = deleteOpportunity;
export const approveAdminOrganizationOpportunity = approveOrganizationOpportunity;
export const rejectAdminOrganizationOpportunity = rejectOrganizationOpportunity;
