import { STATUS_LABELS, TYPE_LABELS } from '../constants/opportunityOptions.js';

const ANONYMOUS_ORGANIZATION_PATTERN = /entreprise\s+anonyme/i;
const NLP_METADATA_KEY_PATTERN = /\b(?:type|organization|organisation|title|location)\s*:\s*/gi;
const LEADING_TYPE_VALUE_PATTERN =
  /^\s*(?:job|stage|internship|research|project|funding)\b[\s,;:|.-]*/i;
const API_BASE_URL = String(import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
const SOURCE_LOGOS_BASE_PATH = '/logos_sites_sources';
const OPPORTUNITY_SOURCE_LOGOS_BASE_PATH = `${SOURCE_LOGOS_BASE_PATH}/logos_opportunities`;
const SOURCE_LOGO_ASSET_RULES = [
  {
    matchers: ['linkedin', 'www.linkedin.com', 'linkedin.com'],
    assetPath: `${OPPORTUNITY_SOURCE_LOGOS_BASE_PATH}/LinkedIn_icon.svg.webp`,
  },
  {
    matchers: ['keejob', 'www.keejob.com', 'keejob.com'],
    assetPath: `${OPPORTUNITY_SOURCE_LOGOS_BASE_PATH}/keejob_logo.jpg`,
  },
  {
    matchers: [
      'haicop',
      'www.haicop.tn',
      'haicop.tn',
      'marchespublics',
      'marches publics',
      'marchespublics.gov.tn',
      'www.marchespublics.gov.tn',
    ],
    assetPath: `${SOURCE_LOGOS_BASE_PATH}/HAICOP.png`,
  },
];
const PLACEHOLDER_LOGO_TOKENS = ['placehold.co', 'placehold.it', 'placeholder', 'text=bidwise'];

const cleanDescription = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return 'No description available';

  const cleaned = raw
    .replace(NLP_METADATA_KEY_PATTERN, ' ')
    .replace(LEADING_TYPE_VALUE_PATTERN, '')
    .replace(/\s+/g, ' ')
    .trim();

  return cleaned || 'No description available';
};

const escapeHtml = (value) =>
  String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

const renderBasicMarkdown = (value) =>
  String(value || '').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

const stripHtmlTags = (value) =>
  String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();

const decodeHtmlEntities = (value) => {
  const rawValue = String(value || '');
  if (!rawValue.includes('&')) return rawValue;
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return rawValue;
  }

  const parser = new DOMParser();
  const doc = parser.parseFromString(`<!doctype html><body>${rawValue}`, 'text/html');
  return String(doc.body?.textContent || '').trim();
};

const truncateText = (text, max = 220) => {
  const normalizedText = String(text || '').trim();
  if (!normalizedText) return '';

  return normalizedText.length > max ? `${normalizedText.slice(0, max)}...` : normalizedText;
};

const sanitizeCompanyLogoUrl = (rawLogo) => {
  const value = String(rawLogo || '').trim();
  if (!value) return '';

  try {
    const url = new URL(value);
    if (url.hostname.includes('media.licdn.com')) {
      url.searchParams.delete('t');
      return url.toString();
    }
  } catch {
    return value;
  }

  return value;
};

const getSourceLogoAsset = (opportunity) => {
  const opportunityType = String(opportunity?.type_opportunite || opportunity?.type || '').trim().toUpperCase();
  const source = opportunity?.source && typeof opportunity.source === 'object' ? opportunity.source : {};
  const sourceName = String(
    source.nom ||
      source.name ||
      opportunity?.source_name ||
      opportunity?.source_label ||
      opportunity?.sourceLabel ||
      '',
  ).trim().toLowerCase();
  const sourceUrl = String(source.url || opportunity?.source_url || '').trim().toLowerCase();
  const sourceItemUrl = String(opportunity?.source_item_url || '').trim().toLowerCase();

  const matchedRule = SOURCE_LOGO_ASSET_RULES.find(({ matchers }) =>
    matchers.some(
      (matcher) =>
        sourceName.includes(matcher) || sourceUrl.includes(matcher) || sourceItemUrl.includes(matcher),
    ),
  );

  if (matchedRule?.assetPath) return matchedRule.assetPath;
  if (opportunityType === 'PROJET') return `${SOURCE_LOGOS_BASE_PATH}/HAICOP.png`;

  return '';
};

const isPlaceholderCompanyLogo = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  return !normalized || PLACEHOLDER_LOGO_TOKENS.some((token) => normalized.includes(token));
};

const getBackendOrigin = () => {
  try {
    return new URL(API_BASE_URL, window.location.origin).origin;
  } catch {
    return window.location.origin;
  }
};

const toSafeNonNegativeInt = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.floor(parsed);
};

export const formatDate = (value) => {
  if (!value) return 'N/A';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString();
};

export const formatRelativeDate = (value) => {
  if (!value) return '';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';

  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.max(0, Math.floor(diffMs / 60000));

  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 12) return `${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`;

  const diffYears = Math.floor(diffMonths / 12);
  return `${diffYears} year${diffYears > 1 ? 's' : ''} ago`;
};

export const formatOrganizationLabel = (opportunity) => {
  const organization = String(opportunity?.organisation_nom || '').trim();
  if (!organization || ANONYMOUS_ORGANIZATION_PATTERN.test(organization)) {
    return '';
  }

  return organization;
};

export const buildCompanyInitialsAvatar = (label) => {
  const words = String(label || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  const initials = words.map((word) => word[0]?.toUpperCase() || '').join('') || 'BW';
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
      <rect width="96" height="96" rx="20" fill="#f1f5f9" />
      <text x="50%" y="52%" dominant-baseline="middle" text-anchor="middle"
        font-family="Arial, sans-serif" font-size="32" font-weight="700" fill="#0f172a">${initials}</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
};

export const getCompanyLogoAsset = (opportunity) => {
  const rawLogo =
    opportunity?.logo_url || opportunity?.organisation_logo || opportunity?.company_logo || '';
  const sanitizedUrl = sanitizeCompanyLogoUrl(rawLogo);
  const sourceLogoAsset = getSourceLogoAsset(opportunity);

  if (isPlaceholderCompanyLogo(sanitizedUrl)) {
    return { src: sourceLogoAsset, fallbackSrc: '' };
  }

  if (sanitizedUrl.startsWith('/media/')) {
    return {
      src: `${getBackendOrigin()}${sanitizedUrl}`,
      fallbackSrc: sourceLogoAsset,
    };
  }

  try {
    const url = new URL(sanitizedUrl);
    if (url.hostname.includes('media.licdn.com')) {
      return {
        src: sanitizedUrl,
        fallbackSrc: sourceLogoAsset,
      };
    }
  } catch {
    return { src: sanitizedUrl, fallbackSrc: sourceLogoAsset };
  }

  return { src: sanitizedUrl, fallbackSrc: sourceLogoAsset };
};

export const formatExperienceLabel = (opportunity) => {
  const experience = opportunity?.experience && typeof opportunity.experience === 'object'
    ? opportunity.experience
    : {
      min: opportunity?.experience_min ?? opportunity?.experience_years,
      max: opportunity?.experience_max ?? opportunity?.experience_years,
    };

  const min = toSafeNonNegativeInt(experience.min);
  const max = toSafeNonNegativeInt(experience.max);

  if (min === null && max === null) return '';
  if (min === 0 && (max === null || max <= 1)) return 'Entry level';
  if (min !== null && max !== null) return min === max ? `${min} years` : `${min}-${max} years`;
  if (min !== null) return `${min}+ years`;

  return `Up to ${max} years`;
};

export const formatProjectDocumentType = (type, fallbackLabel) => {
  const normalizedType = String(type || '').trim().toLowerCase();

  if (normalizedType === 'cahier_des_charges') return 'Cahier des charges';
  if (normalizedType === 'avis_appel_offres') return "Avis d'appel d'offres";
  if (normalizedType === 'autres') return 'Autres documents';

  return String(fallbackLabel || 'Document').trim() || 'Document';
};

export const buildDescriptionMarkup = (opportunity) => {
  const html = String(opportunity?.description_html || '').trim();
  if (html) return renderBasicMarkdown(html);

  return renderBasicMarkdown(escapeHtml(cleanDescription(opportunity?.description))).replace(/\n+/g, '<br />');
};

export const buildDescriptionText = (opportunity) => {
  const html = String(opportunity?.description_html || '').trim();
  if (!html) return cleanDescription(opportunity?.description);

  return decodeHtmlEntities(stripHtmlTags(html));
};

export const buildDescriptionPreview = (opportunity, max = 240) => {
  const htmlDescription = String(opportunity?.description_html || '').trim();
  const sourceText = htmlDescription
    ? decodeHtmlEntities(stripHtmlTags(htmlDescription))
    : cleanDescription(opportunity?.description);

  return truncateText(sourceText, max);
};

export const getOpportunityTypeLabel = (value) => TYPE_LABELS[value] || value || 'N/A';
export const getOpportunityStatusLabel = (value) => STATUS_LABELS[value] || value || 'N/A';

export const getCardAiHint = (opportunity, isUserAuthenticated) => {
  if (!isUserAuthenticated) {
    return 'AI Match locked';
  }

  const raw = Number(opportunity?.similarity_score);
  if (!Number.isFinite(raw)) {
    return 'AI Match in detail';
  }

  const clamped = Math.max(0, Math.min(raw, 1));
  return `AI Match ${Math.round(clamped * 100)}%`;
};

export const formatSimilarityScore = (rawScore) => {
  const score = typeof rawScore === 'number' && !Number.isNaN(rawScore) ? rawScore : 0;
  const clamped = Math.max(0, Math.min(score, 1));
  const percentage = Math.round(clamped * 100);
  let label = 'Related';

  if (percentage >= 75) {
    label = 'High similarity';
  }

  return {
    percentage,
    label,
    raw: clamped.toFixed(2),
  };
};
