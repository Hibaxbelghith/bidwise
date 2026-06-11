import api from '../../../lib/api';

export const fetchMyApplications = async () => {
  const response = await api.get('/me/applications/');
  return Array.isArray(response.data) ? response.data : [];
};

export const withdrawApplication = async (id) => {
  const response = await api.patch(`/me/applications/${id}/withdraw/`, {});
  return response.data;
};