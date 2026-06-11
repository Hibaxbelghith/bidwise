import type { Opportunity } from '../services/opportunitiesService';

const TYPE_LABELS: Record<string, string> = {
  EMPLOI: 'Job',
  STAGE: 'Internship',
  SAISONNIER: 'Seasonal',
  RECHERCHE: 'Research',
  PROJET: 'Project',
  FINANCEMENT: 'Funding',
};

const STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Active',
  EXPIREE: 'Expired',
  ARCHIVEE: 'Archived',
};

const ANONYMOUS_ORGANIZATION_PATTERN = /entreprise\s+anonyme/i;

export function formatDate(value?: string | null): string {
  if (!value) return 'N/A';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return date.toLocaleDateString();
}

export function formatTypeLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return TYPE_LABELS[key] || (key || 'N/A');
}

export function formatStatusLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return STATUS_LABELS[key] || (key || 'N/A');
}

export function getOpportunityTitle(item: Opportunity): string {
  const title = String(item.titre || '').trim();
  return title || 'Untitled opportunity';
}

export function getOrganizationLabel(item: Opportunity): string {
  const organization = String(item.organisation_nom || '').trim();
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

export function formatProjectDocumentType(type?: string | null, fallbackLabel?: string | null): string {
  const normalizedType = String(type || '').trim().toLowerCase();
  if (normalizedType === 'cahier_des_charges') return 'Cahier des charges';
  if (normalizedType === 'avis_appel_offres') return "Avis d'appel d'offres";
  if (normalizedType === 'autres') return 'Autres documents';
  return String(fallbackLabel || '').trim() || 'Document';
}
