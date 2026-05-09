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

const buildLabelMap = (items) =>
  items.reduce((accumulator, item) => {
    accumulator[item.value] = item.label;
    return accumulator;
  }, {});

export const TYPE_LABELS = buildLabelMap(TYPE_OPTIONS);
export const STATUS_LABELS = buildLabelMap(STATUS_OPTIONS);
