const APPLICATION_STATUS_META = {
  SUBMITTED: {
    candidateLabel: 'Under review',
    organizationLabel: 'New',
    candidateDatePrefix: 'Applied',
    className: 'text-blue-600 border-blue-600',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
  },
  VIEWED_BY_ORGANIZATION: {
    candidateLabel: 'Viewed by employer',
    organizationLabel: 'Under review',
    candidateDatePrefix: 'Applied',
    className: 'text-blue-600 border-blue-600',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
  },
  SHORTLISTED: {
    candidateLabel: 'Preselected',
    organizationLabel: 'Preselected',
    candidateDatePrefix: 'Applied',
    className: 'text-green-700 border-green-300',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
  },
  REJECTED: {
    candidateLabel: 'Not selected',
    organizationLabel: 'Rejected',
    candidateDatePrefix: 'Applied',
    className: 'text-red-600 border-red-600',
    bgColor: 'bg-red-100',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
  },
  WITHDRAWN: {
    candidateLabel: 'Application withdrawn',
    organizationLabel: 'Withdrawn',
    candidateDatePrefix: 'Withdrawn',
    className: 'text-neutral-500 border-neutral-300',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
  },
  EXTERNAL_CLICKED: {
    candidateLabel: 'External application started',
    organizationLabel: 'External click',
    candidateDatePrefix: 'Opened',
    className: 'text-amber-700 border-amber-300',
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-200',
  },
  EXTERNAL_APPLIED_CONFIRMED: {
    candidateLabel: 'Applied externally',
    organizationLabel: 'Applied externally',
    candidateDatePrefix: 'Confirmed',
    className: 'text-green-700 border-green-300',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
  },
  EXTERNAL_REMIND_LATER: {
    candidateLabel: 'Saved for later',
    organizationLabel: 'Saved for later',
    candidateDatePrefix: 'Saved',
    className: 'text-neutral-600 border-neutral-300',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
  },
};

const FALLBACK_META = {
  candidateLabel: 'Updated',
  organizationLabel: 'Updated',
  candidateDatePrefix: 'Updated',
  className: 'text-neutral-600 border-neutral-400',
  bgColor: 'bg-gray-100',
  textColor: 'text-gray-700',
  borderColor: 'border-gray-200',
};

export const getApplicationStatusMeta = (status, audience = 'candidate') => {
  const config = APPLICATION_STATUS_META[status] || FALLBACK_META;
  const label =
    audience === 'organization'
      ? config.organizationLabel || config.candidateLabel || status
      : config.candidateLabel || config.organizationLabel || status;

  return {
    label: label || status || 'Updated',
    className: config.className || FALLBACK_META.className,
    bgColor: config.bgColor || FALLBACK_META.bgColor,
    textColor: config.textColor || FALLBACK_META.textColor,
    borderColor: config.borderColor || FALLBACK_META.borderColor,
  };
};

export const getApplicationStatusLabel = (status, audience = 'candidate') =>
  getApplicationStatusMeta(status, audience).label;

export const getApplicationDatePrefix = (status, audience = 'candidate') => {
  const config = APPLICATION_STATUS_META[status] || FALLBACK_META;
  if (audience === 'candidate') {
    return config.candidateDatePrefix || 'Updated';
  }
  return config.organizationDatePrefix || config.candidateDatePrefix || 'Updated';
};
