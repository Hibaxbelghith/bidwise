import { useEffect, useMemo, useState } from 'react';
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
	ArrowLeft, 
	CheckCircle2, 
	Eye, 
	User, 
	Briefcase, 
	Heart, 
	Settings, 
	FileText,
	ChevronRight
} from 'lucide-react';
import { Spinner } from '../../components/ui/spinner.jsx';
import { useAuth } from '../auth/AuthContext.jsx';
import LocationMultiSelect from './components/LocationMultiSelect.jsx';
import ProfileAutocompleteInput from './components/ProfileAutocompleteInput.jsx';
import PreferenceChipGroup from './components/PreferenceChipGroup.jsx';
import ResumeSection from './components/ResumeSection.jsx';
import SalaryExpectationInput from './components/SalaryExpectationInput.jsx';
import {
	EMPLOYMENT_TYPE_OPTIONS,
	OPPORTUNITY_TYPE_OPTIONS,
	WORK_MODE_OPTIONS,
	normalizeLocations,
	normalizeOptionValues,
	normalizeProfilePreferenceData,
	normalizeSkillList,
	normalizeTextList,
} from './profilePreferences.js';
import {
	DEFAULT_COMPENSATION_PERIOD,
	validateSalaryExpectation,
	validateOpportunityTypes,
	validateProfileName,
	validateYearsOfExperience,
} from './profileValidation.js';

const EXPERIENCE_OPTIONS = [
	{ value: 'DEBUTANT', label: 'Débutant (0–1 an)' },
	{ value: 'JUNIOR', label: 'Junior (1–3 ans)' },
	{ value: 'CONFIRME', label: 'Confirmé (3–5 ans)' },
	{ value: 'SENIOR', label: 'Senior (5+ ans)' },
];

const NAV_ITEMS = [
	{ id: 'personal', label: 'Personal Information', icon: User },
	{ id: 'work', label: 'Job Preferences', icon: Briefcase },
	{ id: 'career', label: 'Career Signals', icon: Heart },
	{ id: 'resume', label: 'Resume & CV', icon: FileText },
	{ id: 'settings', label: 'Account Settings', icon: Settings },
];

const Profile = () => {
	const { user, updateUserProfile, refreshUser } = useAuth();
	const profile = user?.profil;
	const profileCompletion = profile?.profile_completion || { score: 0, missing: [] };
	const [formData, setFormData] = useState({
		firstName: '',
		lastName: '',
		experienceLevel: '',
		yearsOfExperience: '',
		salaryExpectation: '',
		salaryPeriod: DEFAULT_COMPENSATION_PERIOD,
	});
	const [skills, setSkills] = useState([]);
	const [interests, setInterests] = useState([]);
	const [targetRoles, setTargetRoles] = useState([]);
	const [opportunityTypes, setOpportunityTypes] = useState([]);
	const [preferredLocations, setPreferredLocations] = useState([]);
	const [workModePreferences, setWorkModePreferences] = useState([]);
	const [employmentTypes, setEmploymentTypes] = useState([]);
	const [profileVisibility, setProfileVisibility] = useState(true);
	const [onboardingCompleted, setOnboardingCompleted] = useState(false);
	const [isLoading, setIsLoading] = useState(false);
	const [showSuccess, setShowSuccess] = useState(false);
	const [formError, setFormError] = useState('');
	const [fieldErrors, setFieldErrors] = useState({});
	const [activeSection, setActiveSection] = useState('personal');
	
	const skillsPayload = useMemo(() => normalizeSkillList(skills), [skills]);
	const interestsPayload = useMemo(() => normalizeTextList(interests), [interests]);
	const targetRolesPayload = useMemo(() => normalizeTextList(targetRoles), [targetRoles]);
	const opportunityTypesPayload = useMemo(
		() => normalizeOptionValues(opportunityTypes, OPPORTUNITY_TYPE_OPTIONS),
		[opportunityTypes]
	);
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
		() => validateSalaryExpectation(formData.salaryExpectation, formData.salaryPeriod),
		[formData.salaryExpectation, formData.salaryPeriod]
	);

	useEffect(() => {
		if (!user) return;
		let onboarding = null;
		try {
			const storedProfile = localStorage.getItem('bidwise_user_profile');
			onboarding = storedProfile ? JSON.parse(storedProfile) : null;
		} catch {
			onboarding = null;
		}

		const backendSkills = normalizeTextList(profile?.competences);
		const backendInterests = normalizeTextList(profile?.domaines_interet);
		const onboardingInterests = Array.isArray(onboarding?.target_roles)
			? onboarding.target_roles.filter(Boolean)
			: [];
		const onboardingPreferences = normalizeProfilePreferenceData(onboarding || {});

		setFormData({
			firstName: profile?.prenom || user?.first_name || '',
			lastName: profile?.nom || user?.last_name || '',
			experienceLevel: profile?.niveau_experience || '',
			yearsOfExperience: profile?.annees_experience?.toString() || '',
			salaryExpectation: profile?.compensation_expectation?.toString() || onboarding?.compensation_expectation?.toString() || '',
			salaryPeriod: profile?.compensation_period || onboarding?.compensation_period || DEFAULT_COMPENSATION_PERIOD,
		});
		setSkills(backendSkills);
		setInterests(backendInterests.length ? backendInterests : onboardingInterests);
		setTargetRoles(normalizeTextList(profile?.target_roles).length ? normalizeTextList(profile?.target_roles) : onboardingInterests);
		setOpportunityTypes(
			normalizeOptionValues(profile?.opportunity_types, OPPORTUNITY_TYPE_OPTIONS).length
				? normalizeOptionValues(profile?.opportunity_types, OPPORTUNITY_TYPE_OPTIONS)
				: onboardingPreferences.opportunity_types
		);
		setPreferredLocations(
			normalizeLocations(profile?.preferred_locations).length
				? normalizeLocations(profile?.preferred_locations)
				: onboardingPreferences.preferred_locations
		);
		setWorkModePreferences(
			normalizeOptionValues(profile?.work_mode_preferences, WORK_MODE_OPTIONS).length
				? normalizeOptionValues(profile?.work_mode_preferences, WORK_MODE_OPTIONS)
				: onboardingPreferences.work_mode_preferences
		);
		setEmploymentTypes(
			normalizeOptionValues(profile?.employment_types, EMPLOYMENT_TYPE_OPTIONS).length
				? normalizeOptionValues(profile?.employment_types, EMPLOYMENT_TYPE_OPTIONS)
				: onboardingPreferences.employment_types
		);
		setProfileVisibility(profile?.profile_visibility ?? onboardingPreferences.profile_visibility);
		setOnboardingCompleted(Boolean(profile?.onboarding_completed));
	}, [profile, user]);

	const handleChange = (field, value) => {
		setFormData((prev) => ({ ...prev, [field]: value }));
		setFieldErrors((prev) => ({ ...prev, [field]: '' }));
	};

	const handleSubmit = async (event) => {
		event.preventDefault();
		setFormError('');
		setFieldErrors({});
		setShowSuccess(false);

		const firstNameValidation = validateProfileName(formData.firstName);
		const lastNameValidation = validateProfileName(formData.lastName);
		const yearsValidation = validateYearsOfExperience(formData.yearsOfExperience);
		const opportunityTypesError = validateOpportunityTypes(opportunityTypesPayload, OPPORTUNITY_TYPE_OPTIONS);
		const nextFieldErrors = {
			firstName: firstNameValidation.error,
			lastName: lastNameValidation.error,
			yearsOfExperience: yearsValidation.error,
			salaryExpectation: salaryValidation.error,
			opportunityTypes: opportunityTypesError,
		};
		const hasFieldErrors = Object.values(nextFieldErrors).some(Boolean);

		if (hasFieldErrors) {
			setFieldErrors(nextFieldErrors);
			return;
		}

		setIsLoading(true);
		const payload = {
			prenom: firstNameValidation.value,
			nom: lastNameValidation.value,
			competences: skillsPayload,
			domaines_interet: interestsPayload,
			niveau_experience: formData.experienceLevel || null,
			annees_experience: yearsValidation.value,
			opportunity_types: opportunityTypesPayload,
			target_roles: targetRolesPayload,
			preferred_locations: preferredLocationsPayload,
			work_mode_preferences: workModePreferencesPayload,
			employment_types: employmentTypesPayload,
			compensation_expectation: salaryValidation.value,
			compensation_currency: 'TND',
			compensation_period: DEFAULT_COMPENSATION_PERIOD,
			profile_visibility: profileVisibility,
			onboarding_completed: onboardingCompleted,
		};

		const result = await updateUserProfile(payload);
		setIsLoading(false);

		if (result.success) {
			localStorage.setItem(
				'bidwise_user_profile',
				JSON.stringify(normalizeProfilePreferenceData(payload))
			);
			setShowSuccess(true);
			setTimeout(() => setShowSuccess(false), 3000);
		} else if (result.error) {
			setFormError(result.error);
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
							<Alert className="border-green-200 bg-green-50">
								<CheckCircle2 className="h-4 w-4 text-green-600" />
								<AlertDescription className="text-green-800">
									Profile updated successfully!
								</AlertDescription>
							</Alert>
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
									<h2 className="text-lg font-semibold text-neutral-900">Personal Information</h2>
									<p className="text-sm text-neutral-500">Your identity and professional background</p>
								</div>
								
								<div className="space-y-4">
									<div className="grid gap-4 sm:grid-cols-2">
										<div className="space-y-1">
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

										<div className="space-y-1">
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

										<div className="space-y-1">
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

									<div>
										<LocationMultiSelect
											id="preferredLocations"
											label="Desired work locations"
											value={preferredLocations}
											onChange={setPreferredLocations}
											placeholder="Add a location"
										/>
									</div>

									<div>
										<SalaryExpectationInput
											label="Minimum desired salary"
											amount={formData.salaryExpectation}
											period={formData.salaryPeriod}
											error={salaryValidation.error}
											onAmountChange={(value) => handleChange('salaryExpectation', value)}
										/>
									</div>

									<div>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">Remote work preferences</Label>
										<PreferenceChipGroup
											options={WORK_MODE_OPTIONS}
											value={workModePreferences}
											onChange={setWorkModePreferences}
										/>
									</div>

									<div>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">Employment type</Label>
										<PreferenceChipGroup
											options={EMPLOYMENT_TYPE_OPTIONS}
											value={employmentTypes}
											onChange={setEmploymentTypes}
										/>
									</div>
								</div>
							</section>

							{/* Section 3: Career Signals */}
							<section id="career" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">Career Signals</h2>
									<p className="text-sm text-neutral-500">Skills and industries you're interested in</p>
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

									<div>
										<ProfileAutocompleteInput
											id="interests"
											label="Industries / Interests"
											termType="interest"
											value={interests}
											onChange={setInterests}
											maxItems={8}
											placeholder="Add an industry"
										/>
									</div>

									<div>
										<Label className="text-sm font-medium text-neutral-700 mb-2 block">Opportunity types</Label>
										<PreferenceChipGroup
											options={OPPORTUNITY_TYPE_OPTIONS}
											value={opportunityTypes}
											onChange={(value) => {
												setOpportunityTypes(value);
												setFieldErrors((prev) => ({ ...prev, opportunityTypes: '' }));
											}}
										/>
										{fieldErrors.opportunityTypes ? (
											<p className="mt-2 text-sm text-red-600" role="alert">
												{fieldErrors.opportunityTypes}
											</p>
										) : null}
									</div>
								</div>
							</section>

							{/* Section 4: Resume */}
							<section id="resume" className="scroll-mt-20 rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
								<div className="border-b border-neutral-200 pb-3 mb-5">
									<h2 className="text-lg font-semibold text-neutral-900">Resume & CV</h2>
									<p className="text-sm text-neutral-500">Upload your resume</p>
								</div>

								<ResumeSection
									profile={profile}
									activeResume={profile?.active_resume}
									onChanged={refreshUser}
								/>
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

									<label className="flex cursor-pointer items-start gap-3">
										<input
											type="checkbox"
											checked={onboardingCompleted}
											onChange={(e) => setOnboardingCompleted(e.target.checked)}
											className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
										/>
										<span className="text-sm text-neutral-700">
											<span className="font-medium">Profile ready for matching</span>
											<span className="block text-xs text-neutral-500">Mark your profile as complete to receive personalized recommendations</span>
										</span>
									</label>
								</div>
							</section>

							{/* Sticky Save Bar */}
							<div className="sticky bottom-4 z-20 rounded-lg border border-neutral-200 bg-white p-4 shadow-lg">
								<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
									<Button type="button" variant="outline" onClick={() => window.history.back()}>
										Cancel
									</Button>
									<Button type="submit" disabled={isLoading || Boolean(salaryValidation.error)}>
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
						</form>
					</main>
				</div>
			</div>
		</div>
	);
};

export default Profile;
