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
	{ value: 'SIVP', label: 'CIVP' },
	{ value: 'FREELANCE', label: 'Freelance' },
];

export const INTERNSHIP_EMPLOYMENT_TYPE_OPTION = { value: 'INTERNSHIP', label: 'Internship' };

export const ALL_EMPLOYMENT_TYPE_OPTIONS = [
	...EMPLOYMENT_TYPE_OPTIONS,
	INTERNSHIP_EMPLOYMENT_TYPE_OPTION,
];

export const getEmploymentTypeOptionsForOpportunityTypes = (opportunityTypes = []) => {
	const selected = new Set(Array.isArray(opportunityTypes) ? opportunityTypes : []);
	return selected.has('INTERNSHIP')
		? ALL_EMPLOYMENT_TYPE_OPTIONS
		: EMPLOYMENT_TYPE_OPTIONS;
};

export const OPPORTUNITY_TYPE_OPTIONS = [
	{ value: 'JOB', label: 'Jobs' },
	{ value: 'INTERNSHIP', label: 'Internships' },
	{ value: 'CALLS_FOR_TENDER', label: 'Calls for tender' },
];

export const normalizeExclusiveOpportunityTypes = (nextValues = [], previousValues = []) => {
	const normalizedNext = normalizeOptionValues(nextValues, OPPORTUNITY_TYPE_OPTIONS);
	const normalizedPrevious = normalizeOptionValues(previousValues, OPPORTUNITY_TYPE_OPTIONS);
	const hadTender = normalizedPrevious.includes('CALLS_FOR_TENDER');
	const hasTender = normalizedNext.includes('CALLS_FOR_TENDER');

	if (!hasTender) return normalizedNext;
	if (!hadTender) return ['CALLS_FOR_TENDER'];

	const nonTenderValues = normalizedNext.filter((value) => value !== 'CALLS_FOR_TENDER');
	return nonTenderValues.length ? nonTenderValues : ['CALLS_FOR_TENDER'];
};

export const TENDER_CATEGORY_OPTIONS = [
	{
		value: 'Biens',
		label: 'Goods',
		subcategories: [
			{ value: 'Autres Fournitures', label: 'Other Supplies' },
			{ value: 'Autres types de matériels', label: 'Other Equipment' },
			{ value: 'Equipements hydromécaniques', label: 'Hydromechanical Equipment' },
			{ value: 'Equipements informatiques', label: 'IT Equipment' },
			{ value: 'Fournitures', label: 'Supplies' },
			{ value: 'Fournitures agricoles', label: 'Agricultural Supplies' },
			{ value: 'Fournitures de bureau', label: 'Office Supplies' },
			{ value: 'Habillement', label: 'Clothing' },
			{ value: 'Matériel', label: 'Equipment' },
			{ value: 'Matériel Médical', label: 'Medical Equipment' },
			{ value: 'Matériel agricole', label: 'Agricultural Equipment' },
			{ value: 'Matériels de Bureau', label: 'Office Equipment' },
			{ value: 'Matériels de reprographie', label: 'Reprography Equipment' },
			{ value: 'Matériels électriques', label: 'Electrical Equipment' },
			{ value: 'Matériels électroniques', label: 'Electronic Equipment' },
			{ value: 'Matériels informatiques', label: 'IT Hardware' },
			{ value: 'Matériels roulants', label: 'Vehicles' },
			{ value: 'Matériels scientifiques', label: 'Scientific Equipment' },
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
			{ value: 'Charpente métallique', label: 'Metal Structure' },
			{ value: 'Climatisation', label: 'Air Conditioning' },
			{ value: 'Electricité', label: 'Electricity' },
			{ value: 'Forages hydrauliques', label: 'Hydraulic Drilling' },
			{ value: 'Fondation Spéciale', label: 'Special Foundation' },
			{ value: 'Génie Civil', label: 'Civil Engineering' },
			{ value: 'Lac collinaire', label: 'Hill Reservoir' },
			{ value: 'Ouvrages hydrauliques', label: 'Hydraulic Works' },
			{ value: 'Peinture et vitrerie', label: 'Painting and Glazing' },
			{ value: 'Pose de canalisation', label: 'Pipeline Installation' },
			{ value: 'Réalisation des réseaux de télécommunication', label: 'Telecommunication Networks' },
			{ value: 'Revêtement routier', label: 'Road Surfacing' },
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
			{ value: 'Activité littéraire et artistique', label: 'Literary and Artistic Activity' },
			{ value: 'Autres études', label: 'Other Studies' },
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
	['marketing', 'marketing_communication'],
	['hr', 'hr_administration'],
	['administration', 'hr_administration'],
	['quality_industry', 'quality_industry_methods'],
	['design', 'design_creative'],
	['legal', 'legal_regulatory'],
]);

const BUSINESS_FAMILY_VALUES = new Set(BUSINESS_FAMILY_OPTIONS.map((option) => option.value));
const BUSINESS_FAMILY_LABELS = new Map(BUSINESS_FAMILY_OPTIONS.map((option) => [option.value, option.label]));

export const getBusinessFamilyLabel = (value) => BUSINESS_FAMILY_LABELS.get(value) || String(value || '');

export const formatBusinessFamilyLabels = (value) =>
	normalizeBusinessFamilyValues(value)
		.map(getBusinessFamilyLabel)
		.filter(Boolean);

export const normalizeBusinessFamilyValues = (value) => {
	const seen = new Set();
	return normalizeTextList(value)
		.map((item) => item.trim())
		.map((item) => {
			const key = item
				.normalize('NFD')
				.replace(/[\u0300-\u036f]/g, '')
				.toLocaleLowerCase()
				.replace(/[-\s]+/g, '_');
			const legacyKey = item
				.normalize('NFD')
				.replace(/[\u0300-\u036f]/g, '')
				.toLocaleLowerCase()
				.replace(/[_-]+/g, ' ')
				.replace(/\s+/g, ' ')
				.trim();
			return BUSINESS_FAMILY_LEGACY_ALIASES.get(legacyKey)
				|| (BUSINESS_FAMILY_VALUES.has(key) ? key : '');
		})
		.filter((item) => {
			if (!item || seen.has(item)) return false;
			seen.add(item);
			return true;
		});
};

export const ONBOARDING_OPPORTUNITY_TYPE_OPTIONS = [
	{
		value: 'JOB',
		label: 'Jobs',
		description: 'CDI, CDD, CIVP and freelance',
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

export const TUNISIAN_LOCATION_OPTIONS = [
	'Tunis',
	'Sidi Bouzid',
	'Sfax',
	'Sousse',
	'Kairouan',
	'Metouia',
	'Kebili',
	'Sukrah',
	'Gabes',
	'Ariana',
	'Sakiet ed Daier',
	'Gafsa',
	'Msaken',
	'Medenine',
	'Beja',
	'Kasserine',
	'Rades',
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
	'Kelibia',
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
	'Jedeida',
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
	'Aine Draham',
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
	opportunity_types: normalizeExclusiveOpportunityTypes(
		normalizeOptionValues(data.opportunity_types, OPPORTUNITY_TYPE_OPTIONS)
	),
	preferred_locations: normalizeLocations(data.preferred_locations),
	work_mode_preferences: normalizeOptionValues(
		data.work_mode_preferences,
		WORK_MODE_OPTIONS
	),
	compensation_expectation: data.compensation_expectation ?? null,
	compensation_min_expectation: data.compensation_min_expectation ?? null,
	compensation_max_expectation: data.compensation_max_expectation ?? null,
	compensation_currency: data.compensation_currency || 'TND',
	compensation_period: data.compensation_period || DEFAULT_COMPENSATION_PERIOD,
	employment_types: normalizeOptionValues(
		data.employment_types,
		ALL_EMPLOYMENT_TYPE_OPTIONS
	),
	target_roles: normalizeTextList(data.target_roles),
	competences: normalizeSkillList(data.competences),
	domaines_interet: normalizeBusinessFamilyValues(data.domaines_interet),
	tender_preferences: data.tender_preferences && typeof data.tender_preferences === 'object'
		? data.tender_preferences
		: { categories: [], max_budget: null },
	profile_visibility: data.profile_visibility ?? true,
});

export const toggleListValue = (list, value) => {
	const current = Array.isArray(list) ? list : [];
	return current.includes(value)
		? current.filter((item) => item !== value)
		: [...current, value];
};
