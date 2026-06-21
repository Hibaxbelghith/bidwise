import {
  BUSINESS_FAMILY_OPTIONS,
  DEFAULT_COMPENSATION_PERIOD,
  ALL_EMPLOYMENT_TYPE_OPTIONS,
  OPPORTUNITY_TYPE_OPTIONS,
  normalizeExclusiveOpportunityTypes,
  TENDER_CATEGORY_OPTIONS,
  WORK_MODE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';

const SKILL_ALIASES = new Map([
  ['css', 'CSS'],
  ['css3', 'CSS'],
  ['js', 'JavaScript'],
  ['javascript', 'JavaScript'],
  ['java script', 'JavaScript'],
  ['py', 'Python'],
  ['python', 'Python'],
  ['react', 'React'],
  ['reactjs', 'React'],
  ['react js', 'React'],
  ['react.js', 'React'],
  ['node', 'Node.js'],
  ['nodejs', 'Node.js'],
  ['node js', 'Node.js'],
  ['node.js', 'Node.js'],
  ['sql', 'SQL'],
]);

const ROLE_REJECT_KEYS = new Set([
  'front',
  'backend',
  'developer',
  'engineer',
  'manager',
  'remote',
  'tunis',
  'urgent',
  'hiring',
]);

const KNOWN_ROLE_KEYS = new Set([
  'frontend developer',
  'backend developer',
  'full stack developer',
  'software engineer',
  'data engineer',
  'data analyst',
  'product manager',
  'project manager',
]);

const BUSINESS_FAMILY_LEGACY_ALIASES = new Map([
  ['ai', 'data_ai'],
  ['ia', 'data_ai'],
  ['bi', 'data_ai'],
  ['fintech', 'accounting_finance_audit'],
  ['finance', 'accounting_finance_audit'],
  ['banque', 'accounting_finance_audit'],
  ['banking', 'accounting_finance_audit'],
  ['assurance', 'accounting_finance_audit'],
  ['insurance', 'accounting_finance_audit'],
  ['health', 'healthcare'],
  ['healthcare', 'healthcare'],
  ['sante', 'healthcare'],
  ['medical', 'healthcare'],
  ['ecommerce', 'sales_business'],
  ['e commerce', 'sales_business'],
  ['e-commerce', 'sales_business'],
  ['saas', 'software_web'],
  ['devops', 'devops_cloud_infrastructure'],
  ['dev ops', 'devops_cloud_infrastructure'],
  ['cloud', 'devops_cloud_infrastructure'],
  ['cloud infrastructure', 'devops_cloud_infrastructure'],
  ['infrastructure cloud', 'devops_cloud_infrastructure'],
  ['docker', 'devops_cloud_infrastructure'],
  ['kubernetes', 'devops_cloud_infrastructure'],
  ['terraform', 'devops_cloud_infrastructure'],
  ['ci cd', 'devops_cloud_infrastructure'],
  ['ci/cd', 'devops_cloud_infrastructure'],
  ['marketing', 'marketing_communication'],
  ['marketing digital', 'marketing_communication'],
  ['communication', 'marketing_communication'],
  ['rh', 'hr_administration'],
  ['hr', 'hr_administration'],
  ['recruitment', 'hr_administration'],
  ['recrutement', 'hr_administration'],
  ['education', 'education_training'],
  ['enseignement', 'education_training'],
  ['training', 'education_training'],
  ['formation', 'education_training'],
  ['tourism', 'sales_business'],
  ['tourisme', 'sales_business'],
  ['cybersecurity', 'security_safety'],
  ['cybersecurite', 'security_safety'],
  ['logistics', 'logistics_supply_chain'],
  ['logistique', 'logistics_supply_chain'],
  ['industry', 'quality_industry_methods'],
  ['industrie', 'quality_industry_methods'],
  ['telecom', 'it_network_support'],
  ['telecommunications', 'it_network_support'],
  ['support it', 'it_network_support'],
  ['it support', 'it_network_support'],
  ['network', 'it_network_support'],
  ['networks', 'it_network_support'],
  ['it_support_network', 'it_network_support'],
  ['accounting_finance', 'accounting_finance_audit'],
  ['sales', 'sales_business'],
  ['administration', 'hr_administration'],
  ['quality_industry', 'quality_industry_methods'],
  ['design', 'design_creative'],
  ['legal', 'legal_regulatory'],
]);

const BUSINESS_FAMILY_VALUES = new Set(BUSINESS_FAMILY_OPTIONS.map((option) => option.value));
const BUSINESS_FAMILY_LABELS = new Map(BUSINESS_FAMILY_OPTIONS.map((option) => [option.value, option.label]));
const toBusinessFamilyKey = (value: unknown) => normalizeTermKey(value).replace(/\s+/g, '_');

export const SALARY_LIMITS_BY_PERIOD: Record<string, { min: number; max: number }> = {
  MONTHLY: { min: 200, max: 30000 },
};

export const PROFILE_NAME_ERROR = 'Input must contain between 2 and 100 characters.';
export const YEARS_OF_EXPERIENCE_ERROR = 'Enter a realistic number of years of experience.';

const stripAccents = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

export const normalizeTermKey = (value: unknown) =>
  stripAccents(String(value || ''))
    .trim()
    .replace(/[._/-]+/g, ' ')
    .replace(/[^\w\s+#]/g, ' ')
    .replace(/\s+/g, ' ')
    .toLocaleLowerCase();

export const normalizeTextLabel = (value: unknown) => String(value || '').trim().replace(/\s+/g, ' ');

export const normalizeTextList = (value: unknown) => {
  const items = Array.isArray(value) ? value : [];
  const seen = new Set<string>();

  return items
    .map(normalizeTextLabel)
    .filter((item) => {
      const key = normalizeTermKey(item);
      if (!item || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};

export const canonicalizeSkillLabel = (value: unknown) => {
  const key = normalizeTermKey(value);
  return SKILL_ALIASES.get(key) || normalizeTextLabel(value);
};

export const getBusinessFamilyLabel = (value: unknown) =>
  BUSINESS_FAMILY_LABELS.get(String(value || '')) || normalizeTextLabel(value);

export const isKnownSkillTerm = (value: unknown) => SKILL_ALIASES.has(normalizeTermKey(value));

export const isKnownRoleTerm = (value: unknown) => KNOWN_ROLE_KEYS.has(normalizeTermKey(value));

export const isRoleTermRejected = (value: unknown) => {
  const key = normalizeTermKey(value);
  if (!key) return true;
  if (ROLE_REJECT_KEYS.has(key)) return true;
  return isKnownSkillTerm(key);
};

export const isInterestTermRejected = (value: unknown) => {
  const key = normalizeTermKey(value);
  const familyKey = toBusinessFamilyKey(value);
  if (!key) return true;
  if (isKnownSkillTerm(key) || isKnownRoleTerm(key)) return true;
  return !BUSINESS_FAMILY_LEGACY_ALIASES.has(key) && !BUSINESS_FAMILY_VALUES.has(familyKey);
};

export const isGarbageSkillInput = (value: unknown) => {
  const key = normalizeTermKey(value);
  if (!key) return true;
  if (/^\d+$/.test(key)) return true;
  if (key.length < 2) return true;
  return /^(.)\1{2,}$/.test(key.replace(/\s+/g, ''));
};

export const normalizeSkillList = (value: unknown) => {
  const seen = new Set<string>();
  return normalizeTextList(value)
    .map(canonicalizeSkillLabel)
    .filter((item) => {
      const key = normalizeTermKey(item);
      if (!item || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};

export const normalizeBusinessFamilyValues = (value: unknown) => {
  const seen = new Set<string>();
  return normalizeTextList(value)
    .map((item) => {
      const key = normalizeTermKey(item).replace(/[_-]+/g, ' ');
      const collapsedKey = key.replace(/\s+/g, ' ').trim();
      const familyKey = toBusinessFamilyKey(item);
      const canonical =
        BUSINESS_FAMILY_LEGACY_ALIASES.get(collapsedKey)
        || BUSINESS_FAMILY_LEGACY_ALIASES.get(normalizeTermKey(item))
        || (BUSINESS_FAMILY_VALUES.has(familyKey) ? familyKey : '');
      return canonical;
    })
    .filter((item) => {
      const key = normalizeTermKey(item);
      if (!item || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};

export const formatBusinessFamilyLabels = (value: unknown) =>
  normalizeBusinessFamilyValues(value).map(getBusinessFamilyLabel);

export const normalizeInterestList = (value: unknown) => formatBusinessFamilyLabels(value);

export const normalizeOptionValues = (
  value: unknown,
  options: { value: string }[],
) => {
  const allowed = new Set(options.map((option) => option.value));
  const seen = new Set<string>();

  return normalizeTextList(value)
    .map((item) => item.toUpperCase())
    .filter((item) => {
      if (!allowed.has(item) || seen.has(item)) return false;
      seen.add(item);
      return true;
    });
};

export const normalizeLocations = (value: unknown) => {
  const seen = new Set<string>();
  return normalizeTextList(value)
    .map(normalizeTextLabel)
    .filter((item) => {
      const key = normalizeTermKey(item);
      if (!item || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};

export const normalizeTenderPreferences = (value: unknown) => {
  const raw = value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
  const validCategories = new Map(
    TENDER_CATEGORY_OPTIONS.map((option) => [
      option.value,
      new Set(option.subcategories.map((subcategory) => subcategory.value)),
    ]),
  );
  const categories = Array.isArray(raw.categories)
    ? raw.categories
        .map((item) => {
          const record = item && typeof item === 'object' && !Array.isArray(item)
            ? item as Record<string, unknown>
            : {};
          const category = normalizeTextLabel(record.category);
          const subcategory = normalizeTextLabel(record.subcategory);
          const subcategories = validCategories.get(category);
          if (!subcategories) return null;
          if (category !== 'Autre' && !subcategories.has(subcategory)) return null;
          return { category, subcategory };
        })
        .filter((item): item is { category: string; subcategory: string } => Boolean(item))
    : [];
  const budget = raw.max_budget;

  return {
    categories: categories.slice(0, 1),
    max_budget: budget === '' || budget === undefined ? null : budget as string | number | null,
  };
};

export const normalizeProfilePreferenceData = (data: Record<string, unknown>) => ({
  opportunity_types: normalizeExclusiveOpportunityTypes(
    normalizeOptionValues(data.opportunity_types, OPPORTUNITY_TYPE_OPTIONS),
  ),
  tender_preferences: normalizeTenderPreferences(data.tender_preferences),
  preferred_locations: normalizeLocations(data.preferred_locations),
  work_mode_preferences: normalizeOptionValues(data.work_mode_preferences, WORK_MODE_OPTIONS),
  compensation_expectation:
    data.compensation_expectation === '' || data.compensation_expectation == null
      ? null
      : data.compensation_expectation,
  compensation_min_expectation:
    data.compensation_min_expectation === '' || data.compensation_min_expectation == null
      ? null
      : data.compensation_min_expectation,
  compensation_max_expectation:
    data.compensation_max_expectation === '' || data.compensation_max_expectation == null
      ? null
      : data.compensation_max_expectation,
  compensation_currency: data.compensation_currency || 'TND',
  compensation_period: normalizeCompensationPeriod(data.compensation_period),
  employment_types: normalizeOptionValues(data.employment_types, ALL_EMPLOYMENT_TYPE_OPTIONS),
  target_roles: normalizeTextList(data.target_roles),
  competences: normalizeSkillList(data.competences),
  domaines_interet: normalizeBusinessFamilyValues(data.domaines_interet),
  profile_visibility: data.profile_visibility ?? true,
});

export const parseSalaryInput = (value: unknown) => {
  const raw = String(value ?? '').trim();
  const sign = raw.startsWith('-') ? '-' : '';
  const cleaned = `${sign}${raw.replace(/[^\d]/g, '')}`;
  if (!cleaned || cleaned === '-') return null;
  return Number.parseInt(cleaned, 10);
};

export const normalizeCompensationPeriod = (value: unknown) => {
  const period = String(value || DEFAULT_COMPENSATION_PERIOD).trim().toUpperCase();
  return SALARY_LIMITS_BY_PERIOD[period] ? period : DEFAULT_COMPENSATION_PERIOD;
};

export const validateSalaryExpectation = (
  value: unknown,
  period = DEFAULT_COMPENSATION_PERIOD,
) => {
  const amount = parseSalaryInput(value);
  if (amount === null) return { value: null, error: '' };

  const normalizedPeriod = normalizeCompensationPeriod(period);
  const limits = SALARY_LIMITS_BY_PERIOD[normalizedPeriod];
  if (amount < 0) return { value: amount, error: 'Salary cannot be negative.' };
  if (amount < limits.min) {
    return { value: amount, error: `Enter at least ${limits.min} TND for ${normalizedPeriod.toLowerCase()}.` };
  }
  if (amount > limits.max) {
    return { value: amount, error: `Enter ${limits.max} TND or less for ${normalizedPeriod.toLowerCase()}.` };
  }
  return { value: amount, error: '' };
};

export const validateSalaryRange = (
  minValue: unknown,
  maxValue: unknown,
  period = DEFAULT_COMPENSATION_PERIOD,
) => {
  const minValidation = validateSalaryExpectation(minValue, period);
  if (minValidation.error) return { min: minValidation.value, max: null, error: minValidation.error };

  const maxValidation = validateSalaryExpectation(maxValue, period);
  if (maxValidation.error) return { min: minValidation.value, max: maxValidation.value, error: maxValidation.error };

  if (
    minValidation.value !== null &&
    maxValidation.value !== null &&
    minValidation.value > maxValidation.value
  ) {
    return {
      min: minValidation.value,
      max: maxValidation.value,
      error: 'Maximum salary must be greater than or equal to minimum salary.',
    };
  }

  return { min: minValidation.value, max: maxValidation.value, error: '' };
};

export const validateProfileName = (value: unknown) => {
  const text = String(value || '').trim().replace(/\s+/g, ' ');
  if (!text) {
    return { value: '', error: '' };
  }
  if (text.length < 2 || text.length > 100) {
    return { value: text, error: PROFILE_NAME_ERROR };
  }
  return { value: text, error: '' };
};

export const validateYearsOfExperience = (value: unknown) => {
  if (value === '' || value === null || value === undefined) {
    return { value: null, error: '' };
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0 || parsed > 60) {
    return { value: parsed, error: YEARS_OF_EXPERIENCE_ERROR };
  }
  return { value: parsed, error: '' };
};
