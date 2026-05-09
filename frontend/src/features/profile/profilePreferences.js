import {
	DEFAULT_COMPENSATION_PERIOD,
	canonicalizeSkillLabel,
	normalizeLocationLabel,
} from './profileValidation.js';

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

export const OPPORTUNITY_TYPE_OPTIONS = [
	{ value: 'JOB', label: 'Jobs' },
	{ value: 'INTERNSHIP', label: 'Internships' },
	{ value: 'RESEARCH', label: 'Research projects' },
	{ value: 'FUNDING', label: 'Funding' },
];

export const TUNISIAN_LOCATION_OPTIONS = [
	'Tunis',
	'Sidi Bouzid',
	'Sfax',
	'Sousse',
	'Kairouan',
	'Métouia',
	'Kebili',
	'Sukrah',
	'Gabès',
	'Ariana',
	'Sakiet ed Daier',
	'Gafsa',
	'Msaken',
	'Medenine',
	'Béja',
	'Kasserine',
	'Radès',
	'Hammamet',
	'Tataouine',
	'Monastir',
	'La Marsa',
	'Ben Arous',
	'Sakiet ez Zit',
	'Zarzis',
	'Ben Gardane',
	'Mahdia',
	'Houmt Souk',
	'Fouchana',
	'Le Kram',
	'El Kef',
	'El Hamma',
	'Nabeul',
	'Le Bardo',
	'Djemmal',
	'Korba',
	'Menzel Temime',
	'Ghardimaou',
	'Midoun',
	'Menzel Bourguiba',
	'Manouba',
	'Kélibia',
	'Rass el Djebel',
	'Oued Lill',
	'Moknine',
	'Bir Ali Ben Khalifa',
	'Kelaa Kebira',
	'El Jem',
	'Tebourba',
	'Ksar Hellal',
	'Douz',
	'Bizerte',
	'Jendouba',
	'La Goulette',
	'Jedeïda',
	'Soliman',
	'Hammam Sousse',
	'Sbiba',
	'Tabarka',
	'Sejenane',
	'Metlaoui',
	'Hammam-Lif',
	'Teboulba',
	'Tozeur',
	'Beni Khiar',
	'Dar Chabanne',
	'Aïne Draham',
	'Bou Salem',
	'Ez Zahra',
	'Kalaa Srira',
	'Skhira',
	'Akouda',
	'El Ksar',
	'Mateur',
	'Siliana',
	'Rhennouch',
	'Dahmani',
	'El Alia',
	'Ar Rudayyif',
	'Zaghouan',
];

export const normalizeTextList = (value) => {
	const items = Array.isArray(value) ? value : [];
	const seen = new Set();

	return items
		.map((item) => String(item || '').trim())
		.filter((item) => {
			const key = item.toLocaleLowerCase();
			if (!item || seen.has(key)) return false;
			seen.add(key);
			return true;
		});
};

export const normalizeSkillList = (value) => {
	const seen = new Set();
	return normalizeTextList(value)
		.map(canonicalizeSkillLabel)
		.filter((item) => {
			const key = item.toLocaleLowerCase();
			if (!item || seen.has(key)) return false;
			seen.add(key);
			return true;
		});
};

export const normalizeOptionValues = (value, options) => {
	const allowed = new Set(options.map((option) => option.value));
	const seen = new Set();

	return normalizeTextList(value)
		.map((item) => item.toUpperCase())
		.filter((item) => {
			if (!allowed.has(item) || seen.has(item)) return false;
			seen.add(item);
			return true;
		});
};

export const normalizeLocations = (value) => {
	const seen = new Set();
	return normalizeTextList(value)
		.map(normalizeLocationLabel)
		.filter((item) => {
			const key = item.toLocaleLowerCase();
			if (!item || seen.has(key)) return false;
			seen.add(key);
			return true;
		});
};

export const normalizeProfilePreferenceData = (data = {}) => ({
	opportunity_types: normalizeOptionValues(
		data.opportunity_types,
		OPPORTUNITY_TYPE_OPTIONS
	),
	preferred_locations: normalizeLocations(data.preferred_locations),
	work_mode_preferences: normalizeOptionValues(
		data.work_mode_preferences,
		WORK_MODE_OPTIONS
	),
	compensation_expectation: data.compensation_expectation ?? null,
	compensation_currency: data.compensation_currency || 'TND',
	compensation_period: data.compensation_period || DEFAULT_COMPENSATION_PERIOD,
	employment_types: normalizeOptionValues(
		data.employment_types,
		EMPLOYMENT_TYPE_OPTIONS
	),
	target_roles: normalizeTextList(data.target_roles),
	profile_visibility: data.profile_visibility ?? true,
});

export const toggleListValue = (list, value) => {
	const current = Array.isArray(list) ? list : [];
	return current.includes(value)
		? current.filter((item) => item !== value)
		: [...current, value];
};
