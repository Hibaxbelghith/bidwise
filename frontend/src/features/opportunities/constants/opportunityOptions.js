export const TYPE_OPTIONS = [
  { value: 'EMPLOI', label: 'Job' },
  { value: 'STAGE', label: 'Internship' },
  { value: 'SAISONNIER', label: 'Seasonal' },
  { value: 'RECHERCHE', label: 'Research' },
  { value: 'PROJET', label: 'Project' },
  { value: 'FINANCEMENT', label: 'Funding' },
];

export const STATUS_OPTIONS = [
  { value: 'ACTIVE', label: 'Active' },
  { value: 'EXPIREE', label: 'Expired' },
  { value: 'ARCHIVEE', label: 'Archived' },
];

export const ORDER_OPTIONS = [
  { value: '-date_publication', label: 'Most recent' },
  { value: 'date_publication', label: 'Oldest first' },
  { value: 'date_limite', label: 'Deadline' },
];

const buildLabelMap = (items) =>
  items.reduce((accumulator, item) => {
    accumulator[item.value] = item.label;
    return accumulator;
  }, {});

export const TYPE_LABELS = buildLabelMap(TYPE_OPTIONS);
export const STATUS_LABELS = buildLabelMap(STATUS_OPTIONS);
