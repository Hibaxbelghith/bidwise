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
import LocationMultiSelect from './components/LocationMultiSelect.jsx';
import BusinessFamilySelect from './components/BusinessFamilySelect.jsx';
import ProfileAutocompleteInput from './components/ProfileAutocompleteInput.jsx';
import PreferenceChipGroup from './components/PreferenceChipGroup.jsx';
import ResumeSection from './components/ResumeSection.jsx';
import {
	EMPLOYMENT_TYPE_OPTIONS,
	WORK_MODE_OPTIONS,
	normalizeBusinessFamilyValues,
	normalizeLocations,
	normalizeOptionValues,
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

const EXPERIENCE_OPTIONS = [
	{ value: 'DEBUTANT', label: 'Beginner (0-1 year)' },
	{ value: 'JUNIOR', label: 'Junior (1-3 years)' },
	{ value: 'CONFIRME', label: 'Intermediate (3-5 years)' },
	{ value: 'SENIOR', label: 'Senior (5+ years)' },
];
const NAV_ITEMS = [
	{ id: 'personal', label: 'Personal Information', icon: User },
	{ id: 'work', label: 'Job Preferences', icon: Briefcase },
	{ id: 'resume', label: 'Resume & CV', icon: FileText },
	{ id: 'career', label: 'Career Signals', icon: Heart },
	{ id: 'settings', label: 'Account Settings', icon: Settings },
];

const FIELD_SECTION_BY_ERROR_KEY = {
	firstName: 'personal',
	lastName: 'personal',
	yearsOfExperience: 'personal',
	preferredLocations: 'work',
	salaryExpectation: 'work',
	interests: 'career',
};

const FIELD_ERROR_LABELS = {
	firstName: 'First name',
	lastName: 'Last name',
	yearsOfExperience: 'Years of experience',
	preferredLocations: 'Desired work locations',
	salaryExpectation: 'Expected salary range',
	interests: 'Sectors',
};

const MAX_PREFERRED_LOCATIONS = 10;

const PROFILE_COMPLETION_SUGGESTIONS = [
	{ key: 'resume', label: 'Upload your resume (+15%)', weight: 15 },
	{ key: 'skills', label: 'Add at least one skill', weight: 10 },
	{ key: 'target_roles', label: 'Add a target role', weight: 10 },
	{ key: 'interests', label: 'Choose at least one sector', weight: 10 },
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
	const profile = user?.profil;
	const accountEmail = user?.email || user?.username || '';
	const profileCompletion = profile?.profile_completion || { score: 0, missing: [] };
	const profileCompletionSuggestions = useMemo(() => {
		const missing = new Set(Array.isArray(profileCompletion.missing) ? profileCompletion.missing : []);
		return PROFILE_COMPLETION_SUGGESTIONS
			.filter((suggestion) => missing.has(suggestion.key))
			.sort((a, b) => b.weight - a.weight)
			.slice(0, 3);
	}, [profileCompletion.missing]);
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
	const [preferredLocations, setPreferredLocations] = useState([]);
	const [workModePreferences, setWorkModePreferences] = useState([]);
	const [employmentTypes, setEmploymentTypes] = useState([]);
	const [profileVisibility, setProfileVisibility] = useState(true);
	const [isLoading, setIsLoading] = useState(false);
	const [showSuccess, setShowSuccess] = useState(false);
	const [formError, setFormError] = useState('');
	const [validationSummary, setValidationSummary] = useState('');
	const [fieldErrors, setFieldErrors] = useState({});
	const [activeSection, setActiveSection] = useState('personal');
	
	const skillsPayload = useMemo(() => normalizeSkillList(skills), [skills]);
	const interestsPayload = useMemo(() => normalizeBusinessFamilyValues(interests), [interests]);
	const targetRolesPayload = useMemo(() => normalizeTextList(targetRoles), [targetRoles]);
	const preferredLocationsPayload = useMemo(() => normalizeLocations(preferredLocations), [preferredLocations]);
	const workModePreferencesPayload = useMemo(
		() => normalizeOptionValues(workModePreferences, WORK_MODE_OPTIONS),
		[workModePreferences]
	);
	const employmentTypesPayload = useMemo(
		() => normalizeOptionValues(employmentTypes, EMPLOYMENT_TYPE_OPTIONS),
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
	const locationRequired = workModePreferencesPayload.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID');

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
			setPreferredLocations(nextEditorState.preferredLocations);
			setWorkModePreferences(nextEditorState.workModePreferences);
			setEmploymentTypes(nextEditorState.employmentTypes);
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
			yearsOfExperience: yearsValidation.error,
			salaryExpectation: salaryValidation.error,
			interests:
				interestsPayload.length === 0
					? 'Choose at least one sector.'
					: '',
			preferredLocations:
				preferredLocationsPayload.length > MAX_PREFERRED_LOCATIONS
					? `Choose at most ${MAX_PREFERRED_LOCATIONS} preferred locations.`
					: locationRequired && preferredLocationsPayload.length === 0
						? 'Choose at least one location for on-site or hybrid work.'
						: '',
		};
		const hasFieldErrors = Object.values(nextFieldErrors).some(Boolean);

		if (hasFieldErrors) {
			setFieldErrors(nextFieldErrors);
			setValidationSummary('Please fix the highlighted fields before saving.');
			return;
		}

		setValidationSummary('');
		setIsLoading(true);
		const payload = {
			prenom: firstNameValidation.value,
			nom: lastNameValidation.value,
			competences: skillsPayload,
			domaines_interet: interestsPayload,
			niveau_experience: formData.experienceLevel || null,
			annees_experience: yearsValidation.value,
			target_roles: targetRolesPayload,
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
			setShowSuccess(true);
			setTimeout(() => setShowSuccess(false), 3000);
		} else if (result.error) {
			const backendFieldErrors = parseBackendProfileError(result.error);
			if (Object.values(backendFieldErrors).some(Boolean)) {
				setFieldErrors(backendFieldErrors);
				setValidationSummary('Please fix the highlighted fields before saving.');
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
									<span className="text-sm font-medium text-neutral-900">Profile strength</span>
									<span className="text-sm font-bold text-blue-600">{profileCompletion.score}%</span>
								</div>
								<div className="h-2 overflow-hidden rounded-full bg-neutral-100">
									<div
										className="h-full rounded-full bg-blue-600 transition-all"
										style={{ width: `${Math.min(Math.max(profileCompletion.score || 0, 0), 100)}%` }}
									/>
								</div>
								<p className="mt-3 text-xs text-neutral-500">
									Complete your profile to get better recommendations
								</p>
								{profileCompletionSuggestions.length > 0 ? (
									<ul className="mt-3 space-y-1.5">
										{profileCompletionSuggestions.map((suggestion) => (
											<li key={suggestion.key} className="flex items-center gap-1.5 text-xs text-neutral-600">
												<Plus className="h-3 w-3 shrink-0 text-blue-600" aria-hidden="true" />
												<span>{suggestion.label}</span>
											</li>
										))}
									</ul>
								) : null}
							</div>

							{/* Navigation */}
							<nav className="space-y-0.5">
								{NAV_ITEMS.map(({ id, label, icon: Icon }) => (
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
											{label}
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
				Profile updated successfully!
			</p>
		</div>
	</div>
)}

						{formError && (
							<Alert variant="destructive">
								<AlertDescription>{formError}</AlertDescription>
							</Alert>
						)}

						{validationSummary ? (
							<Alert variant="destructive">
								<AlertDescription>
									{validationSummary}
									{getFirstErrorKey(fieldErrors)
										? ` First issue: ${FIELD_ERROR_LABELS[getFirstErrorKey(fieldErrors)]}.`
										: ''}
								</AlertDescription>
							</Alert>
						) : null}

						<form onSubmit={handleSubmit} className="space-y-6" noValidate>
							{/* Section 1: Personal Information */}
							<section id="personal" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">Personal Information</h2>
									<p className="text-sm text-neutral-500">Your identity and professional background</p>
								</div>
								
								<div className="space-y-4">
									<div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3">
										<div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
											<div>
												
												<div className="mt-1 flex items-center gap-3">
													<Mail className="h-4 w-4 text-neutral-400" aria-hidden="true" />
													<p className="break-all text-sm font-medium text-neutral-900">
														{accountEmail || 'Email unavailable'}
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
											<Label htmlFor="firstName" className="text-sm font-medium text-neutral-700">First name</Label>
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
											<Label htmlFor="lastName" className="text-sm font-medium text-neutral-700">Last name</Label>
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

										<div className="space-y-1">
											<Label htmlFor="experienceLevel" className="text-sm font-medium text-neutral-700">Experience level</Label>
											<Select
												value={formData.experienceLevel}
												onValueChange={(value) => handleChange('experienceLevel', value)}
											>
												<SelectTrigger id="experienceLevel" className="border-neutral-200 bg-white">
													<SelectValue placeholder="Select level" />
												</SelectTrigger>
												<SelectContent>
													{EXPERIENCE_OPTIONS.map((option) => (
														<SelectItem key={option.value} value={option.value}>
															{option.label}
														</SelectItem>
													))}
												</SelectContent>
											</Select>
										</div>

										<div
											ref={(node) => {
												fieldRefs.current.yearsOfExperience = node;
											}}
											className="space-y-1"
										>
											<Label htmlFor="yearsOfExperience" className="text-sm font-medium text-neutral-700">Years of experience</Label>
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
									</div>
								</div>
							</section>

							{/* Section 2: Job Preferences */}
							<section id="work" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">Job Preferences</h2>
									<p className="text-sm text-neutral-500">Tell us what you're looking for</p>
								</div>

								<div className="space-y-5">
									<div>
										<ProfileAutocompleteInput
											id="targetRole"
											label="Desired job titles"
											termType="role"
											value={targetRoles}
											onChange={setTargetRoles}
											maxItems={5}
											placeholder="Add a job title"
										/>
									</div>

									<div
										ref={(node) => {
											fieldRefs.current.preferredLocations = node;
										}}
									>
										<LocationMultiSelect
											id="preferredLocations"
											label="Desired work locations"
											value={preferredLocations}
											onChange={handlePreferredLocationsChange}
											placeholder={locationRequired ? 'Add a location' : 'Optional for remote roles'}
											maxItems={MAX_PREFERRED_LOCATIONS}
										/>
										<p className="mt-2 text-xs text-neutral-500">
											{locationRequired
												? 'Location is required for on-site or hybrid work.'
												: 'Location is optional when you are open to remote work.'}
										</p>
										{fieldErrors.preferredLocations ? (
											<p id="preferredLocations-error" className="mt-2 text-sm text-red-600" role="alert">
												{fieldErrors.preferredLocations}
											</p>
										) : null}
									</div>

									<div
										ref={(node) => {
											fieldRefs.current.salaryExpectation = node;
										}}
									>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">Expected salary range</Label>
										<div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
											<Input
												type="number"
												inputMode="numeric"
												min="0"
												placeholder="Min"
												value={formData.salaryMinExpectation}
												onChange={(event) => handleChange('salaryMinExpectation', event.target.value)}
												aria-label="Minimum expected salary"
												className="border-neutral-200 bg-white"
											/>
											<span className="text-sm text-neutral-400">-</span>
											<Input
												type="number"
												inputMode="numeric"
												min="0"
												placeholder="Max"
												value={formData.salaryMaxExpectation}
												onChange={(event) => handleChange('salaryMaxExpectation', event.target.value)}
												aria-label="Maximum expected salary"
												className="border-neutral-200 bg-white"
											/>
										</div>
										<p className="mt-2 text-sm text-neutral-500">TND/month. Optional.</p>
										{fieldErrors.salaryExpectation || salaryValidation.error ? (
											<p className="mt-2 text-sm text-red-600" role="alert">
												{fieldErrors.salaryExpectation || salaryValidation.error}
											</p>
										) : null}
									</div>

									<div>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">Remote work preferences</Label>
										<PreferenceChipGroup
											options={WORK_MODE_OPTIONS}
											value={workModePreferences}
											onChange={handleWorkModePreferencesChange}
										/>
									</div>

									<div>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">Contract types</Label>
										<PreferenceChipGroup
											options={EMPLOYMENT_TYPE_OPTIONS}
											value={employmentTypes}
											onChange={setEmploymentTypes}
										/>
									</div>
								</div>
							</section>

							{/* Section 3: Resume */}
							<section id="resume" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">Resume & CV</h2>
									<p className="text-sm text-neutral-500">Upload your resume</p>
								</div>

								<ResumeSection
									profile={profile}
									activeResume={profile?.active_resume}
									onChanged={handleResumeChanged}
								/>
							</section>

							{/* Section 4: Career Signals */}
							<section id="career" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">Career Signals</h2>
									<p className="text-sm text-neutral-500">Skills and professional domains used to improve opportunity matching</p>
								</div>

								<div className="space-y-5">
									<div>
										<ProfileAutocompleteInput
											id="skills"
											label="Skills"
											termType="skill"
											value={skills}
											onChange={setSkills}
											placeholder="Add a skill"
										/>
									</div>

									<div
										ref={(node) => {
											fieldRefs.current.interests = node;
										}}
									>
										<BusinessFamilySelect
											id="interests"
											label="Sectors"
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

							{/* Section 5: Account Settings */}
							<section id="settings" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">Account Settings</h2>
									<p className="text-sm text-neutral-500">Manage your profile visibility</p>
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
											<span className="font-medium">Hiring employers can find you</span>
											<span className="block text-xs text-neutral-500">Make your profile visible to recruiters searching for candidates</span>
										</span>
									</label>

								</div>
							</section>

							{/* Sticky Save Bar */}
							<div className="sticky bottom-4 z-20 rounded-lg border border-neutral-200 bg-white p-4 shadow-lg">
								<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
									{validationSummary ? (
										<div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700" role="alert">
											{validationSummary}
											{getFirstErrorKey(fieldErrors)
												? ` ${FIELD_ERROR_LABELS[getFirstErrorKey(fieldErrors)]} needs attention.`
												: ''}
										</div>
									) : (
										<span aria-hidden="true" />
									)}
									<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
									<Button type="button" variant="outline" onClick={() => window.history.back()}>
										Cancel
									</Button>
									<Button
											type="submit"
											
											disabled={isLoading || Boolean(salaryValidation.error)}
										>
											{isLoading ? (
												<>
													<Spinner size={18} className="mr-2" />
													Saving...
												</>
											) : (
												'Save changes'
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
