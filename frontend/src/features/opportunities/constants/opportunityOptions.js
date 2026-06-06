export const TYPE_OPTIONS = [
  { value: 'EMPLOI', label: 'Job' },
  { value: 'STAGE', label: 'Internship' },
  { value: 'SAISONNIER', label: 'Seasonal' },
  { value: 'PROJET', label: 'Calls for tender' },
];

export const STATUS_OPTIONS = [
  { value: 'ACTIVE', label: 'Active' },
  { value: 'PENDING_REVIEW', label: 'Pending review' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'EXPIREE', label: 'Expired' },
  { value: 'ARCHIVEE', label: 'Archived' },
];

const buildLabelMap = (items) =>
  items.reduce((accumulator, item) => {
    accumulator[item.value] = item.label;
    return accumulator;
  }, {});

export const TYPE_LABELS = buildLabelMap(TYPE_OPTIONS);
export const STATUS_LABELS = buildLabelMap(STATUS_OPTIONS);
