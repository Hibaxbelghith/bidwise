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
    description: 'CDI, CDD, SIVP and freelance',
    values: ['JOB'],
  },
  {
    value: 'INTERNSHIP',
    label: 'Internships',
    description: 'Internships and trainee programs',
    values: ['INTERNSHIP'],
  },
  {
    value: 'CALLS_FOR_TENDER',
    label: 'Calls for tender',
    description: 'Public and private tenders',
    values: ['CALLS_FOR_TENDER'],
  },
];

export function normalizeExclusiveOpportunityTypes(
  nextValues: string[] = [],
  previousValues: string[] = [],
): string[] {
  const allowedValues = new Set(OPPORTUNITY_TYPE_OPTIONS.map((option) => option.value));
  const normalizedNext = Array.from(
    new Set(nextValues.map((value) => String(value || '').trim()).filter((value) => allowedValues.has(value))),
  );
  const normalizedPrevious = Array.from(
    new Set(previousValues.map((value) => String(value || '').trim()).filter((value) => allowedValues.has(value))),
  );
  const hadTender = normalizedPrevious.includes('CALLS_FOR_TENDER');
  const hasTender = normalizedNext.includes('CALLS_FOR_TENDER');

  if (!hasTender) return normalizedNext;
  if (!hadTender) return ['CALLS_FOR_TENDER'];

  const nonTenderValues = normalizedNext.filter((value) => value !== 'CALLS_FOR_TENDER');
  return nonTenderValues.length ? nonTenderValues : ['CALLS_FOR_TENDER'];
}

export const TENDER_CATEGORY_OPTIONS = [
  {
    value: 'Biens',
    label: 'Goods',
    subcategories: [
      { value: 'Autres Fournitures', label: 'Other Supplies' },
      { value: 'Autres types de mat\u00e9riels', label: 'Other Equipment' },
      { value: 'Equipements informatiques', label: 'IT Equipment' },
      { value: 'Fournitures', label: 'Supplies' },
      { value: 'Fournitures de bureau', label: 'Office Supplies' },
      { value: 'Habillement', label: 'Clothing' },
      { value: 'Mat\u00e9riel', label: 'Equipment' },
      { value: 'Mat\u00e9riel M\u00e9dical', label: 'Medical Equipment' },
      { value: 'Mat\u00e9riel agricole', label: 'Agricultural Equipment' },
      { value: 'Mat\u00e9riels de Bureau', label: 'Office Equipment' },
      { value: 'Mat\u00e9riels de reprographie', label: 'Reprography Equipment' },
      { value: 'Mat\u00e9riels \u00e9lectriques', label: 'Electrical Equipment' },
      { value: 'Mat\u00e9riels \u00e9lectroniques', label: 'Electronic Equipment' },
      { value: 'Mat\u00e9riels informatiques', label: 'IT Hardware' },
      { value: 'Mat\u00e9riels roulants', label: 'Vehicles' },
      { value: 'Mat\u00e9riels scientifiques', label: 'Scientific Equipment' },
      { value: 'Mobilier', label: 'Furniture' },
      { value: 'Nourriture', label: 'Food Supplies' },
      { value: "Produits d'entretien", label: 'Cleaning Products' },
      { value: 'Produits pharmaceutiques', label: 'Pharmaceutical Products' },
    ],
  },
  {
    value: 'Travaux',
    label: 'Works',
    subcategories: [
      { value: 'Ascenseur', label: 'Elevator' },
      { value: 'Autres travaux', label: 'Other Works' },
      { value: 'Charpente m\u00e9tallique', label: 'Metal Structure' },
      { value: 'Climatisation', label: 'Air Conditioning' },
      { value: 'Electricit\u00e9', label: 'Electricity' },
      { value: 'G\u00e9nie Civil', label: 'Civil Engineering' },
      { value: 'Routes', label: 'Roads' },
      { value: 'Travaux de Rehabilitation', label: 'Rehabilitation Works' },
      { value: 'VRD', label: 'Roads and Utilities' },
    ],
  },
  {
    value: 'Services',
    label: 'Services',
    subcategories: [
      { value: 'Autres services', label: 'Other Services' },
      { value: 'Maintenance', label: 'Maintenance' },
      { value: 'Maintenance technique', label: 'Technical Maintenance' },
      { value: 'Nettoyage', label: 'Cleaning' },
      { value: 'Services', label: 'Services' },
    ],
  },
  {
    value: 'Etudes',
    label: 'Studies',
    subcategories: [
      { value: 'Activit\u00e9 litt\u00e9raire et artistique', label: 'Literary and Artistic Activity' },
      { value: 'Autres \u00e9tudes', label: 'Other Studies' },
      { value: 'Etudes', label: 'Studies' },
      { value: "Etudes d'impact", label: 'Impact Studies' },
      { value: 'Formation', label: 'Training' },
    ],
  },
  { value: 'Autre', label: 'Other', subcategories: [] },
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
  { value: 'SIVP', label: 'SIVP' },
  { value: 'FREELANCE', label: 'Freelance' },
];

export const INTERNSHIP_EMPLOYMENT_TYPE_OPTION = { value: 'INTERNSHIP', label: 'Internship' };

export const ALL_EMPLOYMENT_TYPE_OPTIONS = [
  ...EMPLOYMENT_TYPE_OPTIONS,
  INTERNSHIP_EMPLOYMENT_TYPE_OPTION,
];

export const getEmploymentTypeOptionsForOpportunityTypes = (opportunityTypes: string[] = []) => {
  const selected = new Set(opportunityTypes);
  return selected.has('INTERNSHIP')
    ? ALL_EMPLOYMENT_TYPE_OPTIONS
    : EMPLOYMENT_TYPE_OPTIONS;
};

export const COMPENSATION_PERIOD_OPTIONS = [
  { value: 'MONTHLY', label: 'Monthly', helper: 'Most common in Tunisia' },
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
