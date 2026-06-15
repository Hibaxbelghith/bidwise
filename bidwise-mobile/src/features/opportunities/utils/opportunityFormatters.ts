import type { Opportunity } from '../services/opportunitiesService';

const TYPE_LABELS: Record<string, string> = {
  EMPLOI: 'Job',
  STAGE: 'Internship',
  SAISONNIER: 'Seasonal',
  RECHERCHE: 'Research',
  PROJET: 'Call for tender',
  FINANCEMENT: 'Funding',
};

const STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Active',
  PENDING_REVIEW: 'Pending review',
  REJECTED: 'Rejected',
  SUSPENDUE: 'Suspended',
  FERMEE: 'Closed',
  EXPIREE: 'Expired',
  ARCHIVEE: 'Archived',
};

const WORK_MODE_LABELS: Record<string, string> = {
  REMOTE: 'Remote',
  HYBRID: 'Hybrid',
  ON_SITE: 'On site',
  ONSITE: 'On site',
};

const ANONYMOUS_ORGANIZATION_PATTERN = /entreprise\s+anonyme/i;

export function formatDate(value?: string | null): string {
  if (!value) return 'N/A';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return date.toLocaleDateString();
}

export function formatDateTime(value?: string | null): string {
  if (!value) return 'N/A';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return date.toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function formatTypeLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return TYPE_LABELS[key] || (key || 'N/A');
}

export function formatStatusLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return STATUS_LABELS[key] || (key || 'N/A');
}

export function formatWorkModeLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return WORK_MODE_LABELS[key] || '';
}

export function getOpportunityTitle(item: Opportunity): string {
  const title = String(item.titre || item.title || '').trim();
  return title || 'Untitled opportunity';
}

export function getOrganizationLabel(item: Opportunity): string {
  const organization = String(item.organisation_nom || item.company || '').trim();
  if (!organization || ANONYMOUS_ORGANIZATION_PATTERN.test(organization)) return '';
  return organization;
}

export function getCompanyLogoUrl(item: Opportunity): string {
  return String(item.company_logo || '').trim();
}

export function getDescriptionPreview(item: Opportunity): string {
  const rawDescription = String(item.description || '').trim();
  if (!rawDescription) return 'No description.';

  const cleaned = rawDescription.replace(/\s+/g, ' ').trim();
  return cleaned.length > 150 ? `${cleaned.slice(0, 150)}...` : cleaned;
}

export function getSkillsPreview(item: Opportunity, limit = 4): string[] {
  const values = [
    ...(Array.isArray(item.normalized_skills) ? item.normalized_skills : []),
    ...(Array.isArray(item.skills) ? item.skills : []),
  ];

  const unique: string[] = [];
  const seen = new Set<string>();

  for (const rawValue of values) {
    const value = String(rawValue || '').trim();
    if (!value) continue;
    const key = value.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(value);
    if (unique.length >= limit) break;
  }

  return unique;
}

function stripHtmlTags(value: string): string {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function decodeHtmlEntities(value: string): string {
  return String(value || '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#039;/gi, "'")
    .replace(/&eacute;/gi, 'é')
    .replace(/&egrave;/gi, 'è')
    .replace(/&agrave;/gi, 'à')
    .replace(/&ccedil;/gi, 'ç')
    .replace(/\s+/g, ' ')
    .trim();
}

export function normalizeDescription(item: Opportunity): string {
  const htmlDescription = String(item.description_html || '').trim();
  if (htmlDescription) {
    const plainFromHtml = decodeHtmlEntities(stripHtmlTags(htmlDescription));
    if (plainFromHtml) return plainFromHtml;
  }

  const raw = String(item.description || '').trim();
  if (!raw) return '';

  return raw
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function toSafeNonNegativeInt(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.floor(parsed);
}

export function formatExperienceLabel(item: Opportunity): string {
  const experience = item.experience;
  if (!experience || typeof experience !== 'object') return '';

  const min = toSafeNonNegativeInt(experience.min);
  const max = toSafeNonNegativeInt(experience.max);

  if (min === null && max === null) return '';
  if (min === 0 && (max === null || max <= 1)) return 'Entry level';
  if (min !== null && max !== null) return min === max ? `${min} years` : `${min}-${max} years`;
  if (min !== null) return `${min}+ years`;

  return `Up to ${max} years`;
}

export function formatContractTypeLabel(value?: string | null): string {
  const normalized = String(value || '').trim();
  if (!normalized) return '';
  if (normalized === 'INTERNSHIP') return 'Internship';
  if (normalized === 'TEMPORARY_INTERIM') return 'Temporary / Interim';
  return normalized.replace(/_/g, ' ');
}

export function formatPublishedAgo(value?: string | null): string {
  if (!value) return '';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';

  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) return '';

  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;

  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w ago`;

  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

export function formatProjectDocumentType(type?: string | null, fallbackLabel?: string | null): string {
  const normalizedType = String(type || '').trim().toLowerCase();
  if (normalizedType === 'cahier_des_charges') return 'Cahier des charges';
  if (normalizedType === 'avis_appel_offres') return "Avis d'appel d'offres";
  if (normalizedType === 'autres') return 'Autres documents';
  return String(fallbackLabel || '').trim() || 'Document';
}
