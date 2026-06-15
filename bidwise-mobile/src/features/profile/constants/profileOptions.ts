export const DEFAULT_COMPENSATION_PERIOD = 'MONTHLY';
export const DEFAULT_COMPENSATION_CURRENCY = 'TND';
export const PROFILE_AUTOCOMPLETE_DEBOUNCE_MS = 250;

export const OPPORTUNITY_TYPE_OPTIONS = [
  { value: 'JOB', label: 'Jobs', description: 'Employment opportunities' },
  { value: 'INTERNSHIP', label: 'Internships', description: 'Internship and trainee programs' },
  { value: 'CALLS_FOR_TENDER', label: 'Calls for tender', description: 'Public tenders and project opportunities' },
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
    value: 'CALLS_FOR_TENDER',
    label: 'Calls for tender',
    description: 'Public tenders and project opportunities',
    values: ['CALLS_FOR_TENDER'],
  },
];

export const BUSINESS_FAMILY_OPTIONS = [
  { value: 'software_web', label: 'Software Web', group: 'Technology' },
  { value: 'backend', label: 'Backend Engineering', group: 'Technology' },
  { value: 'frontend', label: 'Frontend Engineering', group: 'Technology' },
  { value: 'fullstack', label: 'Full Stack Engineering', group: 'Technology' },
  { value: 'data_ai', label: 'Data / AI / BI', group: 'Technology' },
  { value: 'devops_cloud_infrastructure', label: 'IT / DevOps / Cloud Infrastructure', group: 'Technology' },
  { value: 'it_network_support', label: 'IT Support / Networks', group: 'Technology' },
  { value: 'security_safety', label: 'Security / HSE / Safety', group: 'Technology' },
  { value: 'accounting_finance_audit', label: 'Accounting / Finance / Audit', group: 'Business' },
  { value: 'sales_business', label: 'Sales / Business Development', group: 'Business' },
  { value: 'marketing_communication', label: 'Marketing / Communication', group: 'Business' },
  { value: 'hr_administration', label: 'HR / Administration', group: 'Business' },
  { value: 'customer_support', label: 'Customer Support', group: 'Business' },
  { value: 'quality_industry_methods', label: 'Quality / Industry Methods', group: 'Operations' },
  { value: 'engineering_construction', label: 'Engineering / Construction', group: 'Operations' },
  { value: 'logistics_supply_chain', label: 'Logistics / Supply Chain', group: 'Operations' },
  { value: 'design_creative', label: 'Design / Creative', group: 'Creative' },
  { value: 'legal_regulatory', label: 'Legal / Compliance', group: 'Regulated Services' },
  { value: 'healthcare', label: 'Healthcare', group: 'Regulated Services' },
  { value: 'education_training', label: 'Education / Training', group: 'Regulated Services' },
  { value: 'other', label: 'Other', group: 'Other' },
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
