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
  EXPIREE: 'Expired',
  ARCHIVEE: 'Archived',
};

export const EDITABLE_ORGANIZATION_OPPORTUNITY_STATUSES = new Set([
  'ACTIVE',
  'PENDING_REVIEW',
  'REJECTED',
  'SUSPENDUE',
]);

export const formatOrganizationOpportunityDate = (value, options = {}) => {
  if (!value) return 'Not set';
  try {
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      ...options,
    }).format(new Date(value));
  } catch {
    return value;
  }
};

export const humanizeOrganizationValue = (value) =>
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

export const organizationOpportunityEditPath = (opportunity) => {
  const typePaths = {
    EMPLOI: 'job',
    STAGE: 'internship',
    SAISONNIER: 'seasonal',
    PROJET: 'call-for-tender',
  };
  const typePath = typePaths[opportunity?.type];
  return typePath && opportunity?.id
    ? `/organization/post/${typePath}/${opportunity.id}/edit`
    : null;
};

export const statusFallbackForAction = (opportunity, action) => {
  if (action === 'suspend') return 'SUSPENDUE';
  if (action === 'close') return 'FERMEE';
  if (action === 'activate' && opportunity.status === 'PENDING_REVIEW') return 'PENDING_REVIEW';
  if (action === 'activate' && opportunity.suspended_from === 'PENDING_REVIEW') return 'PENDING_REVIEW';
  if (
    action === 'activate'
    && opportunity.status === 'FERMEE'
    && ['PENDING_REVIEW', 'REJECTED'].includes(opportunity.closed_from)
  ) {
    return 'PENDING_REVIEW';
  }
  return 'ACTIVE';
};
