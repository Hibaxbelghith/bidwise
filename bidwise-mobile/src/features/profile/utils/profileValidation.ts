import {
  DEFAULT_COMPENSATION_PERIOD,
  EMPLOYMENT_TYPE_OPTIONS,
  OPPORTUNITY_TYPE_OPTIONS,
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

const INTEREST_ALIASES = new Map([
  ['healthcare', 'HEALTHCARE'],
  ['health', 'HEALTHCARE'],
  ['sante', 'HEALTHCARE'],
  ['pharmacie', 'HEALTHCARE'],
  ['medical', 'HEALTHCARE'],
  ['fintech', 'FINTECH'],
  ['banque', 'FINTECH'],
  ['assurance', 'FINTECH'],
  ['ecommerce', 'ECOMMERCE'],
  ['e commerce', 'ECOMMERCE'],
  ['ai', 'AI'],
  ['ia', 'AI'],
  ['education', 'EDUCATION'],
  ['enseignement', 'EDUCATION'],
  ['tourism', 'TOURISM'],
  ['tourisme', 'TOURISM'],
  ['saas', 'SAAS'],
  ['cybersecurity', 'CYBERSECURITY'],
  ['cybersecurite', 'CYBERSECURITY'],
  ['logistics', 'LOGISTICS'],
  ['logistique', 'LOGISTICS'],
  ['industry', 'INDUSTRY'],
  ['industrie', 'INDUSTRY'],
  ['telecom', 'TELECOM'],
  ['telecommunications', 'TELECOM'],
]);

export const SALARY_LIMITS_BY_PERIOD: Record<string, { min: number; max: number }> = {
  MONTHLY: { min: 200, max: 30000 },
  YEARLY: { min: 2400, max: 360000 },
  DAILY: { min: 10, max: 1500 },
  HOURLY: { min: 2, max: 150 },
};

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

export const canonicalizeInterestLabel = (value: unknown) => {
  const key = normalizeTermKey(value);
  return INTEREST_ALIASES.get(key) || normalizeTextLabel(value).toLocaleUpperCase();
};

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
  if (!key) return true;
  if (isKnownSkillTerm(key) || isKnownRoleTerm(key)) return true;
  return !INTEREST_ALIASES.has(key) && !/^[A-Z][A-Z_]+$/.test(normalizeTextLabel(value));
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

export const normalizeInterestList = (value: unknown) => {
  const seen = new Set<string>();
  return normalizeTextList(value)
    .map(canonicalizeInterestLabel)
    .filter((item) => {
      const key = normalizeTermKey(item);
      if (!item || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};

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

export const normalizeProfilePreferenceData = (data: Record<string, unknown>) => ({
  opportunity_types: normalizeOptionValues(data.opportunity_types, OPPORTUNITY_TYPE_OPTIONS),
  preferred_locations: normalizeLocations(data.preferred_locations),
  work_mode_preferences: normalizeOptionValues(data.work_mode_preferences, WORK_MODE_OPTIONS),
  compensation_expectation: data.compensation_expectation ?? null,
  compensation_currency: data.compensation_currency || 'TND',
  compensation_period: data.compensation_period || DEFAULT_COMPENSATION_PERIOD,
  employment_types: normalizeOptionValues(data.employment_types, EMPLOYMENT_TYPE_OPTIONS),
  target_roles: normalizeTextList(data.target_roles),
  competences: normalizeSkillList(data.competences),
  domaines_interet: normalizeInterestList(data.domaines_interet),
  profile_visibility: data.profile_visibility ?? true,
});

export const parseSalaryInput = (value: unknown) => {
  const raw = String(value ?? '').trim();
  const sign = raw.startsWith('-') ? '-' : '';
  const cleaned = `${sign}${raw.replace(/[^\d]/g, '')}`;
  if (!cleaned || cleaned === '-') return null;
  return Number.parseInt(cleaned, 10);
};

export const validateSalaryExpectation = (
  value: unknown,
  period = DEFAULT_COMPENSATION_PERIOD,
) => {
  const amount = parseSalaryInput(value);
  if (amount === null) return { value: null, error: '' };

  const limits = SALARY_LIMITS_BY_PERIOD[period] || SALARY_LIMITS_BY_PERIOD.MONTHLY;
  if (amount < 0) return { value: amount, error: 'Salary cannot be negative.' };
  if (amount < limits.min) {
    return { value: amount, error: `Enter at least ${limits.min} TND for ${period.toLowerCase()}.` };
  }
  if (amount > limits.max) {
    return { value: amount, error: `Enter ${limits.max} TND or less for ${period.toLowerCase()}.` };
  }
  return { value: amount, error: '' };
};
