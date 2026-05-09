import api from '@/src/shared/services/api';
import type { ProfileSuggestion, ProfileTermType } from '@/src/features/profile/types';

export async function getProfile() {
  const response = await api.get('/profile/me/');
  return response.data;
}

export async function updateProfile(data: Record<string, unknown>) {
  const response = await api.put('/profile/me/', data);
  return response.data;
}

const SUGGEST_ENDPOINTS: Record<ProfileTermType, string> = {
  role: '/profile/roles/suggest/',
  skill: '/profile/skills/suggest/',
  interest: '/profile/interests/suggest/',
};

export async function suggestProfileTerms(
  termType: ProfileTermType,
  query: string,
  limit = 8,
  signal?: AbortSignal,
): Promise<ProfileSuggestion[]> {
  const response = await api.get(SUGGEST_ENDPOINTS[termType], {
    params: { q: query, limit },
    signal,
  });
  return Array.isArray(response.data?.results) ? response.data.results : [];
}

export async function uploadProfileResume(asset: { uri: string; name?: string | null; mimeType?: string | null }) {
  const formData = new FormData();
  formData.append('file', {
    uri: asset.uri,
    name: asset.name || 'resume.pdf',
    type: asset.mimeType || 'application/pdf',
  } as unknown as Blob);

  const response = await api.post('/profile/resume/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function deleteProfileResume() {
  await api.delete('/profile/resume/');
}
