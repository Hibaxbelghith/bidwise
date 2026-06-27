const APPLICATION_STATUS_META = {
  SUBMITTED: {
    candidateLabel: 'Application submitted',
    candidateLabelKey: 'applicationSubmitted',
    organizationLabel: 'New',
    organizationLabelKey: 'new',
    candidateDatePrefix: 'Applied',
    candidateDatePrefixKey: 'applied',
    className: 'text-blue-600 border-blue-600',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
  },
  VIEWED_BY_ORGANIZATION: {
    candidateLabel: 'Under review',
    candidateLabelKey: 'underReview',
    organizationLabel: 'Under review',
    organizationLabelKey: 'underReview',
    candidateDatePrefix: 'Applied',
    candidateDatePrefixKey: 'applied',
    className: 'text-blue-600 border-blue-600',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
  },
  SHORTLISTED: {
    candidateLabel: 'Under review',
    candidateLabelKey: 'underReview',
    organizationLabel: 'Preselected',
    organizationLabelKey: 'preselected',
    candidateDatePrefix: 'Applied',
    candidateDatePrefixKey: 'applied',
    className: 'text-green-700 border-green-300',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
  },
  REJECTED: {
    candidateLabel: 'Under review',
    candidateLabelKey: 'underReview',
    organizationLabel: 'Rejected',
    organizationLabelKey: 'rejected',
    candidateDatePrefix: 'Applied',
    candidateDatePrefixKey: 'applied',
    className: 'text-red-600 border-red-600',
    bgColor: 'bg-red-100',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
  },
  WITHDRAWN: {
    candidateLabel: 'Withdrawn by you',
    candidateLabelKey: 'withdrawnByYou',
    organizationLabel: 'Withdrawn',
    organizationLabelKey: 'withdrawn',
    candidateDatePrefix: 'Withdrawn',
    candidateDatePrefixKey: 'withdrawn',
    className: 'text-neutral-500 border-neutral-300',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
  },
  EXTERNAL_CLICKED: {
    candidateLabel: 'External application started',
    candidateLabelKey: 'externalStarted',
    organizationLabel: 'External click',
    organizationLabelKey: 'externalClick',
    candidateDatePrefix: 'Opened',
    candidateDatePrefixKey: 'opened',
    className: 'text-amber-700 border-amber-300',
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-200',
  },
  EXTERNAL_APPLIED_CONFIRMED: {
    candidateLabel: 'Applied externally',
    candidateLabelKey: 'appliedExternally',
    organizationLabel: 'Applied externally',
    organizationLabelKey: 'appliedExternally',
    candidateDatePrefix: 'Confirmed',
    candidateDatePrefixKey: 'confirmed',
    className: 'text-green-700 border-green-300',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
  },
  EXTERNAL_REMIND_LATER: {
    candidateLabel: 'Saved for later',
    candidateLabelKey: 'savedForLater',
    organizationLabel: 'Saved for later',
    organizationLabelKey: 'savedForLater',
    candidateDatePrefix: 'Saved',
    candidateDatePrefixKey: 'saved',
    className: 'text-neutral-600 border-neutral-300',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
  },
};

const FALLBACK_META = {
  candidateLabel: 'Updated',
  candidateLabelKey: 'updated',
  organizationLabel: 'Updated',
  organizationLabelKey: 'updated',
  candidateDatePrefix: 'Updated',
  candidateDatePrefixKey: 'updated',
  className: 'text-neutral-600 border-neutral-400',
  bgColor: 'bg-gray-100',
  textColor: 'text-gray-700',
  borderColor: 'border-gray-200',
};

const translateStatusValue = (t, key, fallback) =>
  typeof t === 'function' && key ? t(`dashboard.${key}`) : fallback;

export const getApplicationStatusMeta = (status, audience = 'candidate', t = null) => {
  const config = APPLICATION_STATUS_META[status] || FALLBACK_META;
  const label =
    audience === 'organization'
      ? translateStatusValue(t, config.organizationLabelKey, config.organizationLabel || config.candidateLabel || status)
      : translateStatusValue(t, config.candidateLabelKey, config.candidateLabel || config.organizationLabel || status);

  return {
    label: label || status || translateStatusValue(t, 'updated', 'Updated'),
    className: config.className || FALLBACK_META.className,
    bgColor: config.bgColor || FALLBACK_META.bgColor,
    textColor: config.textColor || FALLBACK_META.textColor,
    borderColor: config.borderColor || FALLBACK_META.borderColor,
  };
};

export const getApplicationStatusLabel = (status, audience = 'candidate') =>
  getApplicationStatusMeta(status, audience).label;

export const getApplicationDatePrefix = (status, audience = 'candidate', t = null) => {
  const config = APPLICATION_STATUS_META[status] || FALLBACK_META;
  if (audience === 'candidate') {
    return translateStatusValue(t, config.candidateDatePrefixKey, config.candidateDatePrefix || 'Updated');
  }
  return translateStatusValue(
    t,
    config.organizationDatePrefixKey || config.candidateDatePrefixKey,
    config.organizationDatePrefix || config.candidateDatePrefix || 'Updated',
  );
};
