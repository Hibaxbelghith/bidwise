export const DEFAULT_COMPENSATION_PERIOD = 'MONTHLY';
export const DEFAULT_COMPENSATION_CURRENCY = 'TND';
export const PROFILE_AUTOCOMPLETE_DEBOUNCE_MS = 250;

export const OPPORTUNITY_TYPE_OPTIONS = [
  { value: 'JOB', label: 'Jobs', description: 'Employment opportunities' },
  { value: 'INTERNSHIP', label: 'Internships', description: 'Internship and trainee programs' },
  { value: 'RESEARCH', label: 'Research', description: 'Academic and R&D opportunities' },
  { value: 'FUNDING', label: 'Funding', description: 'Grants, scholarships, and programs' },
];

export const ONBOARDING_OPPORTUNITY_TYPE_OPTIONS = [
  {
    value: 'JOB',
    label: 'Jobs',
    description: 'Full-time, part-time, contract, SIVP',
    values: ['JOB'],
  },
  {
    value: 'INTERNSHIP',
    label: 'Internships',
    description: 'Stage et programmes trainee',
    values: ['INTERNSHIP'],
  },
  {
    value: 'PROJECTS',
    label: 'Projects',
    description: "Appels d'offres, financements, R&D",
    values: ['RESEARCH', 'FUNDING'],
  },
];

export const WORK_MODE_OPTIONS = [
  { value: 'REMOTE', label: 'Remote' },
  { value: 'HYBRID', label: 'Hybrid' },
  { value: 'ON_SITE', label: 'On-site' },
];

export const EMPLOYMENT_TYPE_OPTIONS = [
  { value: 'CDI', label: 'CDI' },
  { value: 'CDD', label: 'CDD' },
  { value: 'INTERNSHIP', label: 'Internship' },
  { value: 'SIVP', label: 'SIVP' },
  { value: 'FREELANCE', label: 'Freelance' },
  { value: 'ALTERNANCE', label: 'Alternance' },
  { value: 'TEMPORARY_INTERIM', label: 'Temporary / Interim' },
  { value: 'SEASONAL', label: 'Seasonal' },
  { value: 'PUBLIC_SECTOR', label: 'Public sector' },
];

export const COMPENSATION_PERIOD_OPTIONS = [
  { value: 'MONTHLY', label: 'Monthly', helper: 'Most common in Tunisia' },
  { value: 'YEARLY', label: 'Yearly' },
  { value: 'DAILY', label: 'Daily' },
  { value: 'HOURLY', label: 'Hourly' },
];

export const TUNISIAN_LOCATION_OPTIONS = [
  'Tunis',
  'Sfax',
  'Sousse',
  'Ariana',
  'Ben Arous',
  'Nabeul',
  'Bizerte',
  'Monastir',
  'Kairouan',
  'Gabes',
  'Gafsa',
  'Medenine',
  'Mahdia',
  'Tozeur',
  'Zaghouan',
];
