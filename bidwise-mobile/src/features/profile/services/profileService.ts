import api from '@/src/shared/services/api';
import type { ProfileSuggestion, ProfileTermType } from '@/src/features/profile/types';

type ApiErrorLike = {
  response?: {
    status?: number;
    data?: Record<string, unknown> | null;
  };
};

const PROFILE_FIELD_MESSAGES: Record<string, string> = {
  preferred_locations: 'You can choose up to 10 preferred locations.',
  work_mode_preferences: 'Select valid work mode preferences.',
  opportunity_types: 'Select at least one valid opportunity type.',
  domaines_interet: 'Choose up to 5 valid sectors.',
  competences: 'Please review your skills and remove invalid entries.',
  target_roles: 'Please review your target roles and remove invalid entries.',
  employment_types: 'Select at least one valid employment type.',
  compensation_expectation: 'Enter a valid salary expectation.',
  compensation_min_expectation: 'Enter a valid minimum salary.',
  compensation_max_expectation: 'Enter a valid maximum salary.',
  compensation_period: 'Choose a valid salary period.',
  compensation_currency: 'Choose a valid salary currency.',
  detail: 'Could not save your profile right now.',
  non_field_errors: 'Some profile information needs your attention before continuing.',
};

function toFirstMessage(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || '').trim()).find(Boolean) || '';
  }
  return String(value || '').trim();
}

function isApiErrorLike(error: unknown): error is ApiErrorLike {
  return typeof error === 'object' && error !== null;
}

export function getProfileUpdateErrorMessage(error: unknown, fallback: string): string {
  if (!isApiErrorLike(error)) {
    return fallback;
  }

  const data = error?.response?.data;
  if (!data || typeof data !== 'object') {
    return fallback;
  }

  const prioritizedFields = [
    'preferred_locations',
    'work_mode_preferences',
    'opportunity_types',
    'domaines_interet',
    'competences',
    'target_roles',
    'employment_types',
    'compensation_min_expectation',
    'compensation_max_expectation',
    'compensation_expectation',
    'compensation_period',
    'compensation_currency',
    'non_field_errors',
    'detail',
  ];

  for (const field of prioritizedFields) {
    const message = toFirstMessage((data as Record<string, unknown>)[field]);
    if (!message) continue;

    if (field === 'detail' || field === 'non_field_errors') {
      return PROFILE_FIELD_MESSAGES[field] || message;
    }

    return PROFILE_FIELD_MESSAGES[field] || message;
  }

  return fallback;
}

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
