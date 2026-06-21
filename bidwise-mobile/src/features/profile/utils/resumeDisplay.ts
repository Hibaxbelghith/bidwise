import type { ActiveResume, BidWiseProfile } from '@/src/features/profile/types';

function cleanCloudinarySegment(value: string) {
  return value
    .replace(/\.[a-f0-9]{16,}(?=\.[a-z0-9]+$)/i, '')
    .replace(/[_-]?[a-f0-9]{16,}(?=\.[a-z0-9]+$)/i, '')
    .replace(/%+/g, '%')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function decodeFileName(value: string) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function getResumeDisplayName(
  resume?: ActiveResume | null,
  fallback = 'Profile resume',
) {
  const originalName = String(resume?.metadata?.original_filename || '').trim();
  if (originalName) return decodeFileName(originalName);

  const fileUrl = String(resume?.file_url || '').trim();
  if (!fileUrl) return fallback;

  const withoutQuery = fileUrl.split('?')[0] || '';
  const segment = withoutQuery.split('/').filter(Boolean).pop() || '';
  const decoded = cleanCloudinarySegment(decodeFileName(segment));
  return decoded || fallback;
}

export function getProfileResumeDisplayName(
  profile?: BidWiseProfile | null,
  fallback = 'Profile resume',
) {
  return getResumeDisplayName(profile?.active_resume, fallback);
}
