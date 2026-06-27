export const ORGANIZATION_OPPORTUNITY_TYPE_LABELS = {
  EMPLOI: 'Job',
  STAGE: 'Internship',
  PROJET: 'Call for tender',
  SAISONNIER: 'Seasonal job',
};

export const ORGANIZATION_OPPORTUNITY_STATUS_LABELS = {
  ACTIVE: 'Active',
  PENDING_REVIEW: 'Pending',
  REJECTED: 'Rejected',
  SUSPENDUE: 'Suspended',
  FERMEE: 'Closed',
  INACTIVE: 'Inactive',
  EXPIRED: 'Expired',
  EXPIREE: 'Expired',
  ARCHIVED: 'Archived',
  ARCHIVEE: 'Archived',
};

export const ORGANIZATION_OPPORTUNITY_STATUS_DOT_CLASSES = {
  ACTIVE: 'bg-emerald-500',
  SUSPENDUE: 'bg-amber-500',
  FERMEE: 'bg-red-500',
  PENDING_REVIEW: 'bg-blue-500',
  REJECTED: 'bg-red-500',
  ARCHIVEE: 'bg-neutral-400',
  EXPIREE: 'bg-neutral-400',
};

const VALUE_LABELS = {
  ON_SITE: 'On site',
  ONSITE: 'On site',
  REMOTE: 'Remote',
  HYBRID: 'Hybrid',
  GRADUATION_PROJECT: 'Graduation internship',
  TRAINING: 'Training internship',
  SUMMER: 'Summer internship',
  WINTER: 'Winter',
  SPRING: 'Spring',
  AUTUMN: 'Autumn',
  '1_3_MONTHS': '1 to 3 months',
  '4_6_MONTHS': '4 to 6 months',
  '7_12_MONTHS': '7 to 12 months',
};

export const formatOrganizationOpportunityDate = (value, options = {}, locale = 'en') => {
  if (!value) return 'Not set';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return new Intl.DateTimeFormat(locale, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...options,
  }).format(date);
};

export const formatOrganizationOpportunityValue = (value) => {
  if (value === null || value === undefined || value === '') return 'Not set';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (VALUE_LABELS[value]) return VALUE_LABELS[value];
  return String(value).replaceAll('_', ' ');
};

export const formatOrganizationOpportunityFieldLabel = (value) => String(value || '')
  .replaceAll('_', ' ')
  .replace(/\b\w/g, (character) => character.toUpperCase());
