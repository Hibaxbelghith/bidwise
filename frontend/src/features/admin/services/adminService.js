import adminApi from '../../../lib/adminApi.js';

export const getDashboard = () => adminApi.get('/admin/dashboard/');

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

export const fetchAdminDashboard = getDashboard;
export const fetchAdminOpportunities = getOpportunities;
export const fetchAdminSources = getSources;
export const deleteAdminOpportunity = deleteOpportunity;
