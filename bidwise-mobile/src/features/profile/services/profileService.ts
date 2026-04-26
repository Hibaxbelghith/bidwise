import api from '@/src/shared/services/api';

export async function getProfile() {
  const response = await api.get('/profile/me/');
  return response.data;
}

export async function updateProfile(data: Record<string, unknown>) {
  const response = await api.put('/profile/me/', data);
  return response.data;
}
