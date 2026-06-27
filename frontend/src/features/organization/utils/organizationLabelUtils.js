export const ORGANIZATION_OPPORTUNITY_TYPE_LABEL_KEYS = {
  EMPLOI: 'organization.jobs',
  STAGE: 'organization.internships',
  PROJET: 'organization.callsForTender',
  SAISONNIER: 'organization.seasonalJobs',
};

export const ORGANIZATION_OPPORTUNITY_STATUS_LABEL_KEYS = {
  ACTIVE: 'organization.statusActive',
  PENDING_REVIEW: 'organization.statusPendingReview',
  REJECTED: 'organization.statusRejected',
  SUSPENDUE: 'organization.statusSuspended',
  FERMEE: 'organization.statusClosed',
  INACTIVE: 'organization.statusInactive',
  EXPIRED: 'organization.statusExpired',
  EXPIREE: 'organization.statusExpired',
  ARCHIVED: 'organization.statusArchived',
  ARCHIVEE: 'organization.statusArchived',
};

export const ORGANIZATION_OPPORTUNITY_VALUE_LABEL_KEYS = {
  ON_SITE: 'organization.workModeOnSite',
  ONSITE: 'organization.workModeOnSite',
  REMOTE: 'organization.workModeRemote',
  HYBRID: 'organization.workModeHybrid',
  GRADUATION_PROJECT: 'organization.internshipGraduation',
  TRAINING: 'organization.internshipTraining',
  SUMMER: 'organization.internshipSummer',
  WINTER: 'organization.seasonWinter',
  SPRING: 'organization.seasonSpring',
  AUTUMN: 'organization.seasonAutumn',
  '1_3_MONTHS': 'organization.durationOneToThreeMonths',
  '4_6_MONTHS': 'organization.durationFourToSixMonths',
  '7_12_MONTHS': 'organization.durationSevenToTwelveMonths',
};

const fallbackLabel = (value, fallback) => (
  fallback || String(value || '-').replaceAll('_', ' ')
);

export const getOrganizationOpportunityTypeLabel = (type, t, fallback = '') => {
  const labelKey = ORGANIZATION_OPPORTUNITY_TYPE_LABEL_KEYS[type];
  return labelKey ? t(labelKey) : fallbackLabel(type, fallback);
};

export const getOrganizationOpportunityStatusLabel = (status, t, fallback = '') => {
  const labelKey = ORGANIZATION_OPPORTUNITY_STATUS_LABEL_KEYS[status];
  return labelKey ? t(labelKey) : fallbackLabel(status, fallback);
};

export const getOrganizationOpportunityValueLabel = (value, t, fallback = '') => {
  if (value === null || value === undefined || value === '') return t('organization.notSet');
  if (typeof value === 'boolean') return value ? t('organization.yes') : t('organization.no');

  const labelKey = ORGANIZATION_OPPORTUNITY_VALUE_LABEL_KEYS[value];
  return labelKey ? t(labelKey) : fallbackLabel(value, fallback);
};
