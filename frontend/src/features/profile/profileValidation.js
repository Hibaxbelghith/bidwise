export const DEFAULT_COMPENSATION_PERIOD = 'MONTHLY';
export const PROFILE_AUTOCOMPLETE_DEBOUNCE_MS = 250;

export const COMPENSATION_PERIOD_OPTIONS = [
	{ value: 'MONTHLY', label: 'Monthly', helper: 'Most common in Tunisia' },
	{ value: 'YEARLY', label: 'Yearly' },
	{ value: 'DAILY', label: 'Daily' },
	{ value: 'HOURLY', label: 'Hourly' },
];

export const SALARY_LIMITS_BY_PERIOD = {
	MONTHLY: { min: 200, max: 30000 },
	YEARLY: { min: 2400, max: 360000 },
	DAILY: { min: 10, max: 1500 },
	HOURLY: { min: 2, max: 150 },
};

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
	['e-commerce', 'ECOMMERCE'],
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

const stripAccents = (value) =>
	String(value || '')
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '');

export const normalizeTermKey = (value) =>
	stripAccents(value)
		.trim()
		.replace(/[._/-]+/g, ' ')
		.replace(/[^\w\s+#]/g, ' ')
		.replace(/\s+/g, ' ')
		.toLocaleLowerCase();

export const canonicalizeSkillLabel = (value) => {
	const key = normalizeTermKey(value);
	return SKILL_ALIASES.get(key) || String(value || '').trim().replace(/\s+/g, ' ');
};

export const isKnownSkillTerm = (value) => SKILL_ALIASES.has(normalizeTermKey(value));

export const isKnownRoleTerm = (value) => KNOWN_ROLE_KEYS.has(normalizeTermKey(value));

export const isRoleTermRejected = (value) => {
	const key = normalizeTermKey(value);
	if (!key) return true;
	if (ROLE_REJECT_KEYS.has(key)) return true;
	return isKnownSkillTerm(key);
};

export const canonicalizeInterestLabel = (value) => {
	const key = normalizeTermKey(value);
	return INTEREST_ALIASES.get(key) || String(value || '').trim().replace(/\s+/g, ' ').toLocaleUpperCase();
};

export const isKnownInterestTerm = (value) => INTEREST_ALIASES.has(normalizeTermKey(value));

export const isInterestTermRejected = (value) => {
	const key = normalizeTermKey(value);
	if (!key) return true;
	if (isKnownSkillTerm(key) || isKnownRoleTerm(key)) return true;
	return !isKnownInterestTerm(key) && !/^[A-Z][A-Z_]+$/.test(String(value || '').trim());
};

export const isGarbageSkillInput = (value) => {
	const text = String(value || '').trim();
	const key = normalizeTermKey(text);
	if (!key) return true;
	if (/^\d+$/.test(key)) return true;
	if (key.length < 2) return true;
	if (/^(.)\1{2,}$/.test(key.replace(/\s+/g, ''))) return true;
	return false;
};

export const normalizeLocationLabel = (value) =>
	String(value || '').trim().replace(/\s+/g, ' ');

export const parseSalaryInput = (value) => {
	const raw = String(value ?? '').trim();
	const sign = raw.startsWith('-') ? '-' : '';
	const cleaned = `${sign}${raw.replace(/[^\d]/g, '')}`;
	if (!cleaned || cleaned === '-') return null;
	return Number.parseInt(cleaned, 10);
};

export const validateSalaryExpectation = (value, period = DEFAULT_COMPENSATION_PERIOD) => {
	const amount = parseSalaryInput(value);
	if (amount === null) {
		return { value: null, error: '' };
	}

	const limits = SALARY_LIMITS_BY_PERIOD[period] || SALARY_LIMITS_BY_PERIOD.MONTHLY;
	if (amount < 0) {
		return { value: amount, error: 'Salary cannot be negative.' };
	}
	if (amount < limits.min) {
		return {
			value: amount,
			error: `Enter at least ${limits.min} TND for a ${period.toLocaleLowerCase()} expectation.`,
		};
	}
	if (amount > limits.max) {
		return {
			value: amount,
			error: `Enter ${limits.max} TND or less for a ${period.toLocaleLowerCase()} expectation.`,
		};
	}
	return { value: amount, error: '' };
};

export const buildSalaryHelperText = (period = DEFAULT_COMPENSATION_PERIOD) => {
	const limits = SALARY_LIMITS_BY_PERIOD[period] || SALARY_LIMITS_BY_PERIOD.MONTHLY;
	if (period === 'MONTHLY') {
		return `Use TND/month. Typical Tunisian expectations often range from internship stipends to senior monthly salaries; accepted range ${limits.min}-${limits.max} TND.`;
	}
	return `Use TND for the selected period. Accepted range ${limits.min}-${limits.max} TND.`;
};
