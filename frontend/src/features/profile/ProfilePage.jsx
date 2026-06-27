import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button.jsx';
import { Input } from '../../components/ui/input.jsx';
import { Label } from '../../components/ui/label.jsx';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '../../components/ui/select.jsx';
import { Alert, AlertDescription } from '../../components/ui/alert.jsx';
import { 
	Mail,
	ArrowLeft, 
	CheckCircle2, 
	Eye, 
	User, 
	Briefcase, 
	Heart, 
	Settings, 
	FileText,
	ChevronRight,
	Plus
} from 'lucide-react';
import { Spinner } from '../../components/ui/spinner.jsx';
import { useAuth } from '../auth/AuthContext.jsx';
import { useLanguage } from '../../i18n/LanguageContext.jsx';
import LocationMultiSelect from './components/LocationMultiSelect.jsx';
import BusinessFamilySelect from './components/BusinessFamilySelect.jsx';
import ProfileAutocompleteInput from './components/ProfileAutocompleteInput.jsx';
import PreferenceChipGroup from './components/PreferenceChipGroup.jsx';
import ResumeSection from './components/ResumeSection.jsx';
import StepTenderPreferences from '../onboarding/steps/StepTenderPreferences.jsx';
import {
	ALL_EMPLOYMENT_TYPE_OPTIONS,
	OPPORTUNITY_TYPE_OPTIONS,
	WORK_MODE_OPTIONS,
	getEmploymentTypeOptionsForOpportunityTypes,
	normalizeBusinessFamilyValues,
	normalizeLocations,
	normalizeOptionValues,
	normalizeExclusiveOpportunityTypes,
	normalizeProfilePreferenceData,
	normalizeSkillList,
	normalizeTextList,
} from './profilePreferences.js';
import { buildProfileEditorState } from './profileEditorState.js';
import {
	DEFAULT_COMPENSATION_PERIOD,
	validateSalaryRange,
	validateProfileName,
	validateYearsOfExperience,
} from './profileValidation.js';

const buildExperienceOptions = (t) => [
	{ value: 'DEBUTANT', label: t('profile.beginner') },
	{ value: 'JUNIOR', label: t('profile.junior') },
	{ value: 'CONFIRME', label: t('profile.intermediate') },
	{ value: 'SENIOR', label: t('profile.senior') },
];
const NAV_ITEMS = [
	{ id: 'personal', labelKey: 'profile.personalInformation', icon: User },
	{ id: 'work', labelKey: 'profile.jobPreferences', icon: Briefcase },
	{ id: 'resume', labelKey: 'profile.resumeCv', icon: FileText },
	{ id: 'career', labelKey: 'profile.careerSignals', icon: Heart },
	{ id: 'settings', labelKey: 'profile.accountSettings', icon: Settings },
];

const FIELD_SECTION_BY_ERROR_KEY = {
	firstName: 'personal',
	lastName: 'personal',
	yearsOfExperience: 'personal',
	preferredLocations: 'work',
	salaryExpectation: 'work',
	interests: 'career',
	tenderPreferences: 'work',
};

const getFieldErrorLabels = (t) => ({
	firstName: t('profile.firstName'),
	lastName: t('profile.lastName'),
	yearsOfExperience: t('profile.yearsExperience'),
	preferredLocations: t('profile.desiredWorkLocations'),
	salaryExpectation: t('profile.expectedSalaryRange'),
	interests: t('profile.sectors'),
	tenderPreferences: t('profile.tenderPreferences'),
});

const getProfileNavLabel = (item, tenderOnly, t) => {
	if (tenderOnly && item.id === 'work') return t('profile.tenderPreferences');
	return t(item.labelKey);
};

const MAX_PREFERRED_LOCATIONS = 10;

const PROFILE_COMPLETION_SUGGESTIONS = [
	{ key: 'first_name', labelKey: 'profile.addFirstName', weight: 30 },
	{ key: 'last_name', labelKey: 'profile.addLastName', weight: 30 },
	{ key: 'resume', labelKey: 'profile.uploadResumeBoost', weight: 15 },
	{ key: 'skills', labelKey: 'profile.addSkill', weight: 10 },
	{ key: 'target_roles', labelKey: 'profile.addTargetRole', weight: 10 },
	{ key: 'interests', labelKey: 'profile.chooseSector', weight: 10 },
];

const getFirstErrorKey = (errors) =>
	Object.keys(FIELD_SECTION_BY_ERROR_KEY).find((key) => Boolean(errors[key]));

const BACKEND_PROFILE_FIELD_ERROR_MAP = {
	preferred_locations: 'preferredLocations',
	domaines_interet: 'interests',
	compensation_expectation: 'salaryExpectation',
	compensation_min_expectation: 'salaryExpectation',
	compensation_max_expectation: 'salaryExpectation',
	annees_experience: 'yearsOfExperience',
	prenom: 'firstName',
	nom: 'lastName',
};

const parseBackendProfileError = (message = '') => {
	const nextFieldErrors = {};
	const cleanBackendMessage = (field, value) => {
		if (field === 'preferredLocations' && /at most\s+\d+\s+preferred locations/i.test(value)) {
			return `You can add up to ${MAX_PREFERRED_LOCATIONS} locations.`;
		}
		return value;
	};

	String(message)
		.split(/(?=\b[a-z_]+:)/g)
		.map((part) => part.trim())
		.filter(Boolean)
		.forEach((part) => {
			const match = part.match(/^([a-z_]+):\s*(.+)$/);
			if (!match) return;
			const field = BACKEND_PROFILE_FIELD_ERROR_MAP[match[1]];
			if (!field) return;
			nextFieldErrors[field] = cleanBackendMessage(field, match[2].trim());
		});

	return nextFieldErrors;
};

const Profile = () => {
	const { user, updateUserProfile, refreshUser } = useAuth();
	const { t } = useLanguage();
	const profile = user?.profil;
	const accountEmail = user?.email || user?.username || '';
	const profileCompletion = profile?.profile_completion || { score: 0, missing: [] };
	const lastHydratedEditorStateRef = useRef('');
	const preserveDraftOnResumeRefreshRef = useRef(false);
	const fieldRefs = useRef({});
	const [formData, setFormData] = useState({
		firstName: '',
		lastName: '',
		experienceLevel: '',
		yearsOfExperience: '',
		salaryExpectation: '',
		salaryMinExpectation: '',
		salaryMaxExpectation: '',
		salaryPeriod: DEFAULT_COMPENSATION_PERIOD,
	});
	const [skills, setSkills] = useState([]);
	const [interests, setInterests] = useState([]);
	const [targetRoles, setTargetRoles] = useState([]);
	const [opportunityTypes, setOpportunityTypes] = useState([]);
	const [preferredLocations, setPreferredLocations] = useState([]);
	const [workModePreferences, setWorkModePreferences] = useState([]);
	const [employmentTypes, setEmploymentTypes] = useState([]);
	const [tenderPreferences, setTenderPreferences] = useState({ categories: [], max_budget: null });
	const [profileVisibility, setProfileVisibility] = useState(true);
	const [isLoading, setIsLoading] = useState(false);
	const [showSuccess, setShowSuccess] = useState(false);
	const [formError, setFormError] = useState('');
	const [validationSummary, setValidationSummary] = useState('');
	const [fieldErrors, setFieldErrors] = useState({});
	const [activeSection, setActiveSection] = useState('personal');
	const isTenderOnlyProfile =
		opportunityTypes.length === 1 &&
		opportunityTypes[0] === 'CALLS_FOR_TENDER';
	const profileCompletionSuggestions = useMemo(() => {
		const missing = new Set(Array.isArray(profileCompletion.missing) ? profileCompletion.missing : []);
		if (isTenderOnlyProfile) {
			return PROFILE_COMPLETION_SUGGESTIONS
				.filter((suggestion) => ['first_name', 'last_name'].includes(suggestion.key))
				.filter((suggestion) => missing.has(suggestion.key))
				.sort((a, b) => b.weight - a.weight);
		}
		return PROFILE_COMPLETION_SUGGESTIONS
			.filter((suggestion) => missing.has(suggestion.key))
			.sort((a, b) => b.weight - a.weight)
			.slice(0, 3);
	}, [isTenderOnlyProfile, profileCompletion.missing]);
	const visibleNavItems = isTenderOnlyProfile
		? NAV_ITEMS.filter((item) => ['personal', 'work'].includes(item.id))
		: NAV_ITEMS;
	
	const skillsPayload = useMemo(() => normalizeSkillList(skills), [skills]);
	const interestsPayload = useMemo(() => normalizeBusinessFamilyValues(interests), [interests]);
	const targetRolesPayload = useMemo(() => normalizeTextList(targetRoles), [targetRoles]);
	const preferredLocationsPayload = useMemo(() => normalizeLocations(preferredLocations), [preferredLocations]);
	const workModePreferencesPayload = useMemo(
		() => normalizeOptionValues(workModePreferences, WORK_MODE_OPTIONS),
		[workModePreferences]
	);
	const employmentTypeOptions = useMemo(
		() => getEmploymentTypeOptionsForOpportunityTypes(opportunityTypes),
		[opportunityTypes]
	);
	const employmentTypesPayload = useMemo(
		() => normalizeOptionValues(employmentTypes, ALL_EMPLOYMENT_TYPE_OPTIONS),
		[employmentTypes]
	);
	const salaryValidation = useMemo(
		() => validateSalaryRange(
			formData.salaryMinExpectation,
			formData.salaryMaxExpectation,
			formData.salaryPeriod
		),
		[formData.salaryMinExpectation, formData.salaryMaxExpectation, formData.salaryPeriod]
	);
	const locationRequired =
		!isTenderOnlyProfile &&
		workModePreferencesPayload.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID');
	const experienceOptions = useMemo(() => buildExperienceOptions(t), [t]);
	const fieldErrorLabels = useMemo(() => getFieldErrorLabels(t), [t]);
	const profileStrengthHelpText = isTenderOnlyProfile
		? t('profile.profileSetupHelp')
		: t('profile.profileStrengthHelp');
	const profileStrengthTitle = isTenderOnlyProfile ? t('profile.profileSetup') : t('profile.profileStrength');
	const personalTitle = isTenderOnlyProfile ? t('profile.accountInformation') : t('profile.personalInformation');
	const personalSubtitle = isTenderOnlyProfile
		? t('profile.identityContact')
		: t('profile.identityProfessional');
	const preferencesTitle = isTenderOnlyProfile ? t('profile.tenderPreferences') : t('profile.jobPreferences');
	const preferencesSubtitle = isTenderOnlyProfile
		? t('profile.tenderPrefsDesc')
		: t('profile.jobPrefsDesc');
	const locationLabel = isTenderOnlyProfile ? t('profile.preferredTenderRegions') : t('profile.desiredWorkLocations');
	const locationPlaceholder = isTenderOnlyProfile
		? t('profile.optionalRegion')
		: locationRequired
			? t('profile.addLocation')
			: t('profile.optionalRemote');
	const locationHelperText = isTenderOnlyProfile
		? t('profile.allTenderRegions')
		: locationRequired
			? t('profile.locationRequired')
			: t('profile.locationOptional');
	const fieldErrorLabel = (key) => {
		if (isTenderOnlyProfile && key === 'preferredLocations') {
			return t('profile.preferredTenderRegions');
		}
		return fieldErrorLabels[key];
	};

	const handleInterestsChange = (values) => {
		setInterests(values);
		setFieldErrors((prev) => ({ ...prev, interests: '' }));
		setValidationSummary('');
	};

	useEffect(() => {
		if (!user) return;
		let storedProfile = null;
		try {
			const persistedProfile = localStorage.getItem('bidwise_user_profile');
			storedProfile = persistedProfile ? JSON.parse(persistedProfile) : null;
		} catch {
			storedProfile = null;
		}

		const nextEditorState = buildProfileEditorState({
			user,
			profile,
			storedProfile,
		});
		const nextEditorStateKey = JSON.stringify(nextEditorState);
		const shouldPreserveDraft =
			preserveDraftOnResumeRefreshRef.current
			&& lastHydratedEditorStateRef.current === nextEditorStateKey;

		if (!shouldPreserveDraft) {
			setFormData(nextEditorState.formData);
			setSkills(nextEditorState.skills);
			setInterests(nextEditorState.interests);
			setTargetRoles(nextEditorState.targetRoles);
			setOpportunityTypes(nextEditorState.opportunityTypes);
			setPreferredLocations(nextEditorState.preferredLocations);
			setWorkModePreferences(nextEditorState.workModePreferences);
		setEmploymentTypes(nextEditorState.employmentTypes);
			setTenderPreferences(nextEditorState.tenderPreferences || { categories: [], max_budget: null });
			setProfileVisibility(nextEditorState.profileVisibility);
		}

		lastHydratedEditorStateRef.current = nextEditorStateKey;
		preserveDraftOnResumeRefreshRef.current = false;
	}, [profile, user]);

	const handleResumeChanged = async (options = {}) => {
		const preserveDraft = options?.preserveDraft !== false;
		preserveDraftOnResumeRefreshRef.current = preserveDraft;
		const result = await refreshUser();
		if (!result?.success) {
			preserveDraftOnResumeRefreshRef.current = false;
		}
		return result;
	};

	useEffect(() => {
		const refreshResumeState = () => {
			handleResumeChanged({ preserveDraft: true });
		};

		window.addEventListener('bidwise:resume-updated', refreshResumeState);
		if (localStorage.getItem('bidwise_resume_updated_at')) {
			localStorage.removeItem('bidwise_resume_updated_at');
			refreshResumeState();
		}

		return () => {
			window.removeEventListener('bidwise:resume-updated', refreshResumeState);
		};
	}, []);

	const handleChange = (field, value) => {
		setFormData((prev) => ({ ...prev, [field]: value }));
		setFieldErrors((prev) => ({ ...prev, [field]: '' }));
		setValidationSummary('');
	};

	const handlePreferredLocationsChange = (locations) => {
		setPreferredLocations(locations);
		setFieldErrors((prev) => ({ ...prev, preferredLocations: '' }));
		setValidationSummary('');
	};

	const handleWorkModePreferencesChange = (values) => {
		setWorkModePreferences(values);
		const normalizedValues = normalizeOptionValues(values, WORK_MODE_OPTIONS);
		const nextLocationRequired = normalizedValues.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID');

		if (!nextLocationRequired) {
			setFieldErrors((prev) => ({ ...prev, preferredLocations: '' }));
			setValidationSummary('');
		}
	};

	const handleOpportunityTypesChange = (values) => {
		const normalizedValues = normalizeExclusiveOpportunityTypes(values, opportunityTypes);
		setOpportunityTypes(normalizedValues);
		const allowedEmploymentTypes = new Set(
			getEmploymentTypeOptionsForOpportunityTypes(normalizedValues).map((option) => option.value)
		);
		setEmploymentTypes((prev) => prev.filter((value) => allowedEmploymentTypes.has(value)));
		if (normalizedValues.length === 1 && normalizedValues[0] === 'CALLS_FOR_TENDER') {
			setFieldErrors((prev) => ({
				...prev,
				yearsOfExperience: '',
				salaryExpectation: '',
				interests: '',
				preferredLocations: '',
			}));
			setValidationSummary('');
		}
	};

	const handleTenderPreferencesChange = (field, value) => {
		if (field !== 'tender_preferences') return;
		setTenderPreferences(value && typeof value === 'object' ? value : { categories: [], max_budget: null });
		setFieldErrors((prev) => ({ ...prev, tenderPreferences: '' }));
		setValidationSummary('');
	};

	useEffect(() => {
		const allowed = new Set(employmentTypeOptions.map((option) => option.value));
		setEmploymentTypes((prev) => prev.filter((value) => allowed.has(value)));
	}, [employmentTypeOptions]);

	useEffect(() => {
		if (!validationSummary) return undefined;

		const firstErrorKey = getFirstErrorKey(fieldErrors);
		if (!firstErrorKey) return undefined;

		const sectionId = FIELD_SECTION_BY_ERROR_KEY[firstErrorKey];
		if (sectionId) {
			setActiveSection(sectionId);
		}

		const frame = window.requestAnimationFrame(() => {
			const target = fieldRefs.current[firstErrorKey] || document.getElementById(sectionId);
			if (!target) return;

			target.scrollIntoView({ behavior: 'smooth', block: 'center' });
			const focusTarget = target.querySelector(
				'input, button, [role="combobox"], textarea, select, [tabindex]:not([tabindex="-1"])'
			);
			focusTarget?.focus?.({ preventScroll: true });
		});

		return () => window.cancelAnimationFrame(frame);
	}, [fieldErrors, validationSummary]);

	const handleSubmit = async (event) => {
		event.preventDefault();
		setFormError('');
		setFieldErrors({});
		setShowSuccess(false);

		const firstNameValidation = validateProfileName(formData.firstName);
		const lastNameValidation = validateProfileName(formData.lastName);
		const yearsValidation = validateYearsOfExperience(formData.yearsOfExperience);
		const nextFieldErrors = {
			firstName: firstNameValidation.error,
			lastName: lastNameValidation.error,
			yearsOfExperience: isTenderOnlyProfile ? '' : yearsValidation.error,
			salaryExpectation: isTenderOnlyProfile ? '' : salaryValidation.error,
			interests:
				!isTenderOnlyProfile && interestsPayload.length === 0
					? t('profile.chooseSector')
					: '',
			preferredLocations:
				preferredLocationsPayload.length > MAX_PREFERRED_LOCATIONS
					? `Choose at most ${MAX_PREFERRED_LOCATIONS} preferred locations.`
					: locationRequired && preferredLocationsPayload.length === 0
						? 'Choose at least one location for on-site or hybrid work.'
						: '',
			tenderPreferences: '',
		};
		if (isTenderOnlyProfile) {
			const firstTenderCategory = Array.isArray(tenderPreferences?.categories)
				? tenderPreferences.categories[0]
				: null;
			const maxBudget = tenderPreferences?.max_budget;
			if (!firstTenderCategory?.category) {
				nextFieldErrors.tenderPreferences = 'Select a tender category.';
			} else if (firstTenderCategory.category !== 'Autre' && !firstTenderCategory.subcategory) {
				nextFieldErrors.tenderPreferences = 'Select a tender subcategory.';
			} else if (maxBudget !== null && maxBudget !== '' && Number(maxBudget) < 0) {
				nextFieldErrors.tenderPreferences = 'Enter a positive maximum caution budget.';
			}
		}
		const hasFieldErrors = Object.values(nextFieldErrors).some(Boolean);

		if (hasFieldErrors) {
			setFieldErrors(nextFieldErrors);
			setValidationSummary(t('profile.fixHighlighted'));
			return;
		}

		setValidationSummary('');
		setIsLoading(true);
		const normalizedOpportunityTypes = normalizeOptionValues(opportunityTypes, OPPORTUNITY_TYPE_OPTIONS);
		const payload = isTenderOnlyProfile ? {
			prenom: firstNameValidation.value,
			nom: lastNameValidation.value,
			opportunity_types: ['CALLS_FOR_TENDER'],
			tender_preferences: tenderPreferences,
			preferred_locations: preferredLocationsPayload,
			domaines_interet: [],
			competences: [],
			niveau_experience: null,
			annees_experience: null,
			target_roles: [],
			work_mode_preferences: [],
			employment_types: [],
			compensation_expectation: null,
			compensation_min_expectation: null,
			compensation_max_expectation: null,
			compensation_currency: 'TND',
			compensation_period: DEFAULT_COMPENSATION_PERIOD,
			profile_visibility: profileVisibility,
		} : {
			prenom: firstNameValidation.value,
			nom: lastNameValidation.value,
			competences: skillsPayload,
			domaines_interet: interestsPayload,
			niveau_experience: formData.experienceLevel || null,
			annees_experience: yearsValidation.value,
			target_roles: targetRolesPayload,
			opportunity_types: normalizedOpportunityTypes,
			preferred_locations: preferredLocationsPayload,
			work_mode_preferences: workModePreferencesPayload,
			employment_types: employmentTypesPayload,
			compensation_expectation: salaryValidation.min ?? salaryValidation.max,
			compensation_min_expectation: salaryValidation.min,
			compensation_max_expectation: salaryValidation.max,
			compensation_currency: 'TND',
			compensation_period: DEFAULT_COMPENSATION_PERIOD,
			profile_visibility: profileVisibility,
		};

		const result = await updateUserProfile(payload);
		setIsLoading(false);

		if (result.success) {
			const refreshedResult = await refreshUser();
			const persistedProfile = refreshedResult?.data?.profil || result.data?.profil || payload;
			localStorage.setItem(
				'bidwise_user_profile',
				JSON.stringify(normalizeProfilePreferenceData(persistedProfile))
			);
			setSkills(normalizeTextList(persistedProfile.competences));
			setInterests(normalizeBusinessFamilyValues(persistedProfile.domaines_interet));
			setTargetRoles(normalizeTextList(persistedProfile.target_roles));
			setOpportunityTypes(normalizeOptionValues(persistedProfile.opportunity_types, OPPORTUNITY_TYPE_OPTIONS));
			setTenderPreferences(
				persistedProfile.tender_preferences && typeof persistedProfile.tender_preferences === 'object'
					? persistedProfile.tender_preferences
					: { categories: [], max_budget: null }
			);
			setShowSuccess(true);
			setTimeout(() => setShowSuccess(false), 3000);
		} else if (result.error) {
			const backendFieldErrors = parseBackendProfileError(result.error);
			if (Object.values(backendFieldErrors).some(Boolean)) {
				setFieldErrors(backendFieldErrors);
				setValidationSummary(t('profile.fixHighlighted'));
			} else {
				setFormError(result.error);
			}
		}
	};

	const scrollToSection = (sectionId) => {
		setActiveSection(sectionId);
		const element = document.getElementById(sectionId);
		if (element) {
			const headerOffset = 80;
			const elementPosition = element.getBoundingClientRect().top;
			const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
			
			window.scrollTo({
				top: offsetPosition,
				behavior: 'smooth'
			});
		}
	};

	return (
		<div className="min-h-screen bg-neutral-100">
			<div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
				{/* Header 
				<div className="mb-6">
					<Link
						to="/opportunities"
						className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
					>
						<ArrowLeft className="h-4 w-4" />
						Back to opportunities
					</Link>
				</div> 
				*/}

				<div className="flex flex-col gap-8 lg:flex-row lg:gap-12">
					{/* Sidebar Navigation */}
					<aside className="lg:w-64 lg:shrink-0">
						<div className="sticky top-8 space-y-6">
							{/* Profile completion card */}
							<div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
								<div className="flex items-center justify-between mb-3">
									<span className="text-sm font-medium text-neutral-900">{profileStrengthTitle}</span>
									<span className="text-sm font-bold text-blue-600">{profileCompletion.score}%</span>
								</div>
								<div className="h-2 overflow-hidden rounded-full bg-neutral-100">
									<div
										className="h-full rounded-full bg-blue-600 transition-all"
										style={{ width: `${Math.min(Math.max(profileCompletion.score || 0, 0), 100)}%` }}
									/>
								</div>
								<p className="mt-3 text-xs text-neutral-500">
									{profileStrengthHelpText}
								</p>
								{profileCompletionSuggestions.length > 0 ? (
									<ul className="mt-3 space-y-1.5">
										{profileCompletionSuggestions.map((suggestion) => (
											<li key={suggestion.key} className="flex items-center gap-1.5 text-xs text-neutral-600">
												<Plus className="h-3 w-3 shrink-0 text-blue-600" aria-hidden="true" />
												<span>{t(suggestion.labelKey)}</span>
											</li>
										))}
									</ul>
								) : null}
							</div>

							{/* Navigation */}
							<nav className="space-y-0.5">
								{visibleNavItems.map(({ id, labelKey, icon: Icon }) => (
									<button
										key={id}
										onClick={() => scrollToSection(id)}
										className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors ${
											activeSection === id
												? 'bg-white text-neutral-900 font-medium shadow-sm border border-neutral-200'
												: 'text-neutral-600 hover:bg-white hover:text-neutral-900 hover:shadow-sm'
										}`}
									>
										<span className="flex items-center gap-2">
											<Icon className="h-4 w-4" />
											{getProfileNavLabel({ id, labelKey }, isTenderOnlyProfile, t)}
										</span>
										<ChevronRight className={`h-3.5 w-3.5 ${activeSection === id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`} />
									</button>
								))}
							</nav>
						</div>
					</aside>

					{/* Main Content */}
					<main className="flex-1 space-y-6">
						{/* Success Alert */}
						{showSuccess && (
	<div className="fixed bottom-6 left-6 z-50 animate-in fade-in slide-in-from-bottom-2">
		<div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3 shadow-lg">
			<CheckCircle2 className="h-5 w-5 text-green-600" />
			<p className="text-sm font-medium text-green-800">
				{t('profile.updated')}
			</p>
		</div>
	</div>
)}

						{formError && (
							<Alert variant="destructive">
								<AlertDescription>{formError}</AlertDescription>
							</Alert>
						)}

						<form onSubmit={handleSubmit} className="space-y-6" noValidate>
							{/* Section 1: Personal Information */}
							<section id="personal" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">{personalTitle}</h2>
									<p className="text-sm text-neutral-500">{personalSubtitle}</p>
								</div>
								
								<div className="space-y-4">
									<div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3">
										<div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
											<div>
												
												<div className="mt-1 flex items-center gap-3">
													<Mail className="h-4 w-4 text-neutral-400" aria-hidden="true" />
													<p className="break-all text-sm font-medium text-neutral-900">
														{accountEmail || t('profile.unavailableEmail')}
													</p>
												</div>
											</div>
										</div>
									</div>

									<div className="grid gap-4 sm:grid-cols-2">
										<div
											ref={(node) => {
												fieldRefs.current.firstName = node;
											}}
											className="space-y-1"
										>
											<Label htmlFor="firstName" className="text-sm font-medium text-neutral-700">{t('profile.firstName')}</Label>
											<Input
												id="firstName"
												type="text"
												minLength={2}
												maxLength={100}
												value={formData.firstName}
												onChange={(event) => handleChange('firstName', event.target.value)}
												aria-invalid={Boolean(fieldErrors.firstName)}
												aria-describedby="firstName-error"
												className="border-neutral-200 bg-white"
											/>
											{fieldErrors.firstName ? (
												<p id="firstName-error" className="text-sm text-red-600" role="alert">
													{fieldErrors.firstName}
												</p>
											) : null}
										</div>

										<div
											ref={(node) => {
												fieldRefs.current.lastName = node;
											}}
											className="space-y-1"
										>
											<Label htmlFor="lastName" className="text-sm font-medium text-neutral-700">{t('profile.lastName')}</Label>
											<Input
												id="lastName"
												type="text"
												minLength={2}
												maxLength={100}
												value={formData.lastName}
												onChange={(event) => handleChange('lastName', event.target.value)}
												aria-invalid={Boolean(fieldErrors.lastName)}
												aria-describedby="lastName-error"
												className="border-neutral-200 bg-white"
											/>
											{fieldErrors.lastName ? (
												<p id="lastName-error" className="text-sm text-red-600" role="alert">
													{fieldErrors.lastName}
												</p>
											) : null}
										</div>

										{!isTenderOnlyProfile ? (
										<div className="space-y-1">
											<Label htmlFor="experienceLevel" className="text-sm font-medium text-neutral-700">{t('profile.experienceLevel')}</Label>
											<Select
												value={formData.experienceLevel}
												onValueChange={(value) => handleChange('experienceLevel', value)}
											>
												<SelectTrigger id="experienceLevel" className="border-neutral-200 bg-white">
													<SelectValue placeholder={t('profile.selectLevel')} />
												</SelectTrigger>
												<SelectContent>
													{experienceOptions.map((option) => (
														<SelectItem key={option.value} value={option.value}>
															{option.label}
														</SelectItem>
													))}
												</SelectContent>
											</Select>
										</div>
										) : null}

										{!isTenderOnlyProfile ? (
										<div
											ref={(node) => {
												fieldRefs.current.yearsOfExperience = node;
											}}
											className="space-y-1"
										>
											<Label htmlFor="yearsOfExperience" className="text-sm font-medium text-neutral-700">{t('profile.yearsExperience')}</Label>
											<Input
												id="yearsOfExperience"
												type="number"
												min="0"
												max="60"
												step="1"
												value={formData.yearsOfExperience}
												onChange={(event) => handleChange('yearsOfExperience', event.target.value)}
												aria-invalid={Boolean(fieldErrors.yearsOfExperience)}
												aria-describedby="yearsOfExperience-error"
												className="border-neutral-200 bg-white"
											/>
											{fieldErrors.yearsOfExperience ? (
												<p id="yearsOfExperience-error" className="text-sm text-red-600" role="alert">
													{fieldErrors.yearsOfExperience}
												</p>
											) : null}
										</div>
										) : null}
									</div>
								</div>
							</section>

							{/* Section 2: Preferences */}
							<section id="work" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">{preferencesTitle}</h2>
									<p className="text-sm text-neutral-500">{preferencesSubtitle}</p>
								</div>

								<div className="space-y-5">
									{!isTenderOnlyProfile ? (
									<div>
										<ProfileAutocompleteInput
											id="targetRole"
											label={t('profile.desiredJobTitles')}
											termType="role"
											value={targetRoles}
											onChange={setTargetRoles}
											maxItems={5}
											placeholder={t('profile.addJobTitle')}
										/>
									</div>
									) : null}

									<div
										ref={(node) => {
											fieldRefs.current.preferredLocations = node;
										}}
									>
										<LocationMultiSelect
											id="preferredLocations"
											label={locationLabel}
											value={preferredLocations}
											onChange={handlePreferredLocationsChange}
											placeholder={locationPlaceholder}
											maxItems={MAX_PREFERRED_LOCATIONS}
										/>
										<p className="mt-2 text-xs text-neutral-500">
											{locationHelperText}
										</p>
										{fieldErrors.preferredLocations ? (
											<p id="preferredLocations-error" className="mt-2 text-sm text-red-600" role="alert">
												{fieldErrors.preferredLocations}
											</p>
										) : null}
									</div>

									{!isTenderOnlyProfile ? (
									<div
										ref={(node) => {
											fieldRefs.current.salaryExpectation = node;
										}}
									>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">{t('profile.expectedSalaryRange')}</Label>
										<div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
											<Input
												type="number"
												inputMode="numeric"
												min="0"
												placeholder={t('profile.min')}
												value={formData.salaryMinExpectation}
												onChange={(event) => handleChange('salaryMinExpectation', event.target.value)}
												aria-label={t('profile.minSalary')}
												className="border-neutral-200 bg-white"
											/>
											<span className="text-sm text-neutral-400">-</span>
											<Input
												type="number"
												inputMode="numeric"
												min="0"
												placeholder={t('profile.max')}
												value={formData.salaryMaxExpectation}
												onChange={(event) => handleChange('salaryMaxExpectation', event.target.value)}
												aria-label={t('profile.maxSalary')}
												className="border-neutral-200 bg-white"
											/>
										</div>
										<p className="mt-2 text-sm text-neutral-500">{t('profile.tndMonthOptional')}</p>
										{fieldErrors.salaryExpectation || salaryValidation.error ? (
											<p className="mt-2 text-sm text-red-600" role="alert">
												{fieldErrors.salaryExpectation || salaryValidation.error}
											</p>
										) : null}
									</div>
									) : null}

									{!isTenderOnlyProfile ? (
									<div>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">{t('profile.remoteWorkPreferences')}</Label>
										<PreferenceChipGroup
											options={WORK_MODE_OPTIONS}
											value={workModePreferences}
											onChange={handleWorkModePreferencesChange}
										/>
									</div>
									) : null}

									<div>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">{t('profile.opportunityTypes')}</Label>
										<PreferenceChipGroup
											options={OPPORTUNITY_TYPE_OPTIONS}
											value={opportunityTypes}
											onChange={handleOpportunityTypesChange}
										/>
									</div>

									{isTenderOnlyProfile ? (
									<div
										ref={(node) => {
											fieldRefs.current.tenderPreferences = node;
										}}
										className="rounded-md border border-neutral-200 bg-neutral-50 p-4"
									>
										<StepTenderPreferences
											data={{ tender_preferences: tenderPreferences }}
											onChange={handleTenderPreferencesChange}
											error={fieldErrors.tenderPreferences}
										/>
									</div>
									) : null}

									{!isTenderOnlyProfile ? (
									<div>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">{t('profile.contractTypes')}</Label>
										<PreferenceChipGroup
											options={employmentTypeOptions}
											value={employmentTypes}
											onChange={setEmploymentTypes}
										/>
									</div>
									) : null}
								</div>
							</section>

							{/* Section 3: Resume */}
							{!isTenderOnlyProfile ? (
							<section id="resume" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">{t('profile.resumeCv')}</h2>
									<p className="text-sm text-neutral-500">{t('profile.uploadResume')}</p>
								</div>

								<ResumeSection
									profile={profile}
									activeResume={profile?.active_resume}
									onChanged={handleResumeChanged}
								/>
							</section>
							) : null}

							{/* Section 4: Career Signals */}
							{!isTenderOnlyProfile ? (
							<section id="career" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">{t('profile.careerSignals')}</h2>
									<p className="text-sm text-neutral-500">{t('profile.careerSignalsDesc')}</p>
								</div>

								<div className="space-y-5">
									{!isTenderOnlyProfile ? (
									<div>
										<ProfileAutocompleteInput
											id="skills"
											label={t('profile.skills')}
											termType="skill"
											value={skills}
											onChange={setSkills}
											placeholder={t('profile.addSkillPlaceholder')}
										/>
									</div>
									) : null}

									<div
										ref={(node) => {
											fieldRefs.current.interests = node;
										}}
									>
										<BusinessFamilySelect
											id="interests"
											label={t('profile.sectors')}
											value={interests}
											onChange={handleInterestsChange}
											maxItems={5}
										/>
										{fieldErrors.interests ? (
											<p id="interests-error" className="mt-2 text-sm text-red-600" role="alert">
												{fieldErrors.interests}
											</p>
										) : null}
									</div>
								</div>
							</section>
							) : null}

							{/* Section 5: Account Settings */}
							{!isTenderOnlyProfile ? (
							<section id="settings" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">{t('profile.accountSettings')}</h2>
									<p className="text-sm text-neutral-500">{t('profile.visibilityDesc')}</p>
								</div>

								<div className="space-y-4">
									<label className="flex cursor-pointer items-start gap-3">
										<input
											type="checkbox"
											checked={profileVisibility}
											onChange={(e) => setProfileVisibility(e.target.checked)}
											className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
										/>
										<span className="text-sm text-neutral-700">
											<span className="font-medium">{t('profile.employersCanFind')}</span>
											<span className="block text-xs text-neutral-500">{t('profile.visibilityHelp')}</span>
										</span>
									</label>

								</div>
							</section>
							) : null}

							{/* Sticky Save Bar */}
							<div className="sticky bottom-4 z-20 rounded-lg border border-neutral-200 bg-white p-4 shadow-lg">
								<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
									{validationSummary ? (
										<div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700" role="alert">
											{validationSummary}
											{getFirstErrorKey(fieldErrors)
												? ` ${t('profile.needsAttention', { field: fieldErrorLabel(getFirstErrorKey(fieldErrors)) })}`
												: ''}
										</div>
									) : (
										<span aria-hidden="true" />
									)}
									<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
									<Button type="button" variant="outline" onClick={() => window.history.back()}>
										{t('profile.cancel')}
									</Button>
									<Button
											type="submit"
											
											disabled={isLoading || (!isTenderOnlyProfile && Boolean(salaryValidation.error))}
										>
											{isLoading ? (
												<>
													<Spinner size={18} className="mr-2" />
													{t('profile.saving')}
												</>
											) : (
												t('profile.saveChanges')
											)}
									</Button>
									</div>
								</div>
							</div>
						</form>
					</main>
				</div>
			</div>
		</div>
	);
};

export default Profile;
