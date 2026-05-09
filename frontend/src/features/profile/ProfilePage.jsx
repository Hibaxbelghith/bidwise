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
import { Checkbox } from '../../components/ui/checkbox.jsx';
import { Alert, AlertDescription } from '../../components/ui/alert.jsx';
import { ArrowLeft, CheckCircle2, Eye, Sparkles } from 'lucide-react';
import { Spinner } from '../../components/ui/spinner.jsx';
import { useAuth } from '../auth/AuthContext.jsx';
import LocationMultiSelect from './components/LocationMultiSelect.jsx';
import ProfileAutocompleteInput from './components/ProfileAutocompleteInput.jsx';
import ProfileSection from './components/ProfileSection.jsx';
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
} from './profileValidation.js';

const EXPERIENCE_OPTIONS = [
	{ value: 'DEBUTANT', label: 'Débutant (0–1 an)' },
	{ value: 'JUNIOR', label: 'Junior (1–3 ans)' },
	{ value: 'CONFIRME', label: 'Confirmé (3–5 ans)' },
	{ value: 'SENIOR', label: 'Senior (5+ ans)' },
];

const Profile = () => {
	const { user, updateUserProfile, refreshUser } = useAuth();
	const profile = user?.profil;
	const profileCompletion = profile?.profile_completion || { score: 0, missing: [] };
	const missingCompletion = Array.isArray(profileCompletion.missing) ? profileCompletion.missing.slice(0, 3) : [];
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
	};

	const handleSubmit = async (event) => {
		event.preventDefault();
		setFormError('');
		setShowSuccess(false);

		if (salaryValidation.error) {
			setFormError(salaryValidation.error);
			return;
		}

		setIsLoading(true);
		const payload = {
			prenom: formData.firstName,
			nom: formData.lastName,
			competences: skillsPayload,
			domaines_interet: interestsPayload,
			niveau_experience: formData.experienceLevel || null,
			annees_experience: formData.yearsOfExperience
				? Number(formData.yearsOfExperience)
				: null,
			opportunity_types: opportunityTypesPayload,
			target_roles: targetRolesPayload,
			preferred_locations: preferredLocationsPayload,
			work_mode_preferences: workModePreferencesPayload,
			employment_types: employmentTypesPayload,
			compensation_expectation: salaryValidation.value,
			compensation_currency: 'TND',
			compensation_period: formData.salaryPeriod || DEFAULT_COMPENSATION_PERIOD,
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

	return (
		<div className="min-h-screen bg-neutral-50">
			<div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
				<div className="mb-8">
					<Link
						to="/opportunities"
						className="mb-4 inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900"
					>
						<ArrowLeft className="h-4 w-4" />
						Back to opportunities
					</Link>
					<h1 className="mb-2 text-3xl font-bold text-neutral-900">My Profile</h1>
					<p className="text-neutral-600">
						Keep your profile up to date to get better opportunity recommendations
					</p>
				</div>

				<div className="mb-6 rounded-md border border-neutral-200 bg-white p-4">
					<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
						<div>
							<p className="text-sm font-medium text-neutral-900">
								{profileCompletion.score}% complete
							</p>
							<p className="text-sm text-neutral-500">
								{missingCompletion.length
									? `Next: ${missingCompletion.join(', ')}`
									: 'Your profile has the core signals needed for matching.'}
							</p>
						</div>
						<div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100 sm:w-56">
							<div
								className="h-full rounded-full bg-blue-600 transition-all"
								style={{ width: `${Math.min(Math.max(profileCompletion.score || 0, 0), 100)}%` }}
							/>
						</div>
					</div>
				</div>

				{showSuccess && (
					<Alert className="mb-6 border-green-200 bg-green-50">
						<CheckCircle2 className="h-4 w-4 text-green-600" />
						<AlertDescription className="text-green-800">
							Profile updated successfully!
						</AlertDescription>
					</Alert>
				)}

				{formError && (
					<Alert variant="destructive" className="mb-6">
						<AlertDescription>{formError}</AlertDescription>
					</Alert>
				)}

				<form onSubmit={handleSubmit} className="space-y-5 pb-24">
					<ProfileSection
						title="Basic Information"
						description="Personal identity and experience signals."
						defaultOpen
					>
						<div className="grid gap-4 sm:grid-cols-2">
							<div className="space-y-2">
								<Label htmlFor="firstName">First name</Label>
								<Input
									id="firstName"
									type="text"
									value={formData.firstName}
									onChange={(event) => handleChange('firstName', event.target.value)}
								/>
							</div>

							<div className="space-y-2">
								<Label htmlFor="lastName">Last name</Label>
								<Input
									id="lastName"
									type="text"
									value={formData.lastName}
									onChange={(event) => handleChange('lastName', event.target.value)}
								/>
							</div>

							<div className="space-y-2">
								<Label htmlFor="experienceLevel">Experience level</Label>
								<Select
									value={formData.experienceLevel}
									onValueChange={(value) => handleChange('experienceLevel', value)}
								>
									<SelectTrigger id="experienceLevel">
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

							<div className="space-y-2">
								<Label htmlFor="yearsOfExperience">Years of experience</Label>
								<Input
									id="yearsOfExperience"
									type="number"
									inputMode="numeric"
									min="0"
									max="50"
									value={formData.yearsOfExperience}
									onChange={(event) => handleChange('yearsOfExperience', event.target.value)}
								/>
							</div>
						</div>
					</ProfileSection>

					<ProfileSection
						title="Work Preferences"
						description="Market, location, employment, and compensation filters."
						defaultOpen
					>
						<div className="space-y-2">
							<Label>Opportunity types</Label>
							<PreferenceChipGroup
								options={OPPORTUNITY_TYPE_OPTIONS}
								value={opportunityTypes}
								onChange={setOpportunityTypes}
							/>
						</div>

						<LocationMultiSelect
							id="preferredLocations"
							value={preferredLocations}
							onChange={setPreferredLocations}
							placeholder="Search Tunis, Sfax, Sousse..."
						/>

						<div className="space-y-2">
							<Label>Work modes</Label>
							<PreferenceChipGroup
								options={WORK_MODE_OPTIONS}
								value={workModePreferences}
								onChange={setWorkModePreferences}
							/>
						</div>

						<div className="space-y-2">
							<Label>Employment types</Label>
							<PreferenceChipGroup
								options={EMPLOYMENT_TYPE_OPTIONS}
								value={employmentTypes}
								onChange={setEmploymentTypes}
							/>
						</div>

						<SalaryExpectationInput
							amount={formData.salaryExpectation}
							period={formData.salaryPeriod}
							error={salaryValidation.error}
							onAmountChange={(value) => handleChange('salaryExpectation', value)}
							onPeriodChange={(value) => handleChange('salaryPeriod', value)}
						/>
					</ProfileSection>

					<ProfileSection
						title="Career Signals"
						description="Structured signals used by autocomplete, matching, and future recommendations."
						defaultOpen
					>
						<div className="rounded-md bg-neutral-50 p-3 text-sm text-neutral-600">
							Skills are what you can do. Interests are industries or domains you want to work in.
						</div>

						<ProfileAutocompleteInput
							id="targetRole"
							label="Target roles"
							termType="role"
							value={targetRoles}
							onChange={setTargetRoles}
							maxItems={5}
							placeholder="Search Frontend Developer, Backend Developer..."
						/>

						<ProfileAutocompleteInput
							id="skills"
							label="Skills"
							termType="skill"
							value={skills}
							onChange={setSkills}
							placeholder="Search React, Python, CSS..."
							emptyText="No skills added yet."
						/>

						<ProfileAutocompleteInput
							id="interests"
							label="Industries / Interests"
							termType="interest"
							value={interests}
							onChange={setInterests}
							maxItems={8}
							placeholder="Search Healthcare, Fintech, AI..."
							emptyText="No interests added yet."
						/>
					</ProfileSection>

					<ProfileSection
						title="Resume / CV"
						description="Upload a resume or build a structured BidWise resume from your profile."
						defaultOpen
					>
						<ResumeSection
							profile={profile}
							activeResume={profile?.active_resume}
							onChanged={refreshUser}
						/>
					</ProfileSection>

					<ProfileSection
						title="Profile Settings"
						description="Visibility and completion controls."
						defaultOpen={false}
					>
						<label className="flex cursor-pointer items-start gap-3 rounded-md border border-neutral-200 bg-white p-4">
							<Checkbox
								checked={profileVisibility}
								onChange={(event) => setProfileVisibility(event.target.checked)}
								aria-describedby="visibility-helper"
							/>
							<span>
								<span className="flex items-center gap-1.5 font-medium text-neutral-900">
									<Eye className="h-4 w-4 text-neutral-500" aria-hidden="true" />
									Profile visible to recruiters
								</span>
								<span id="visibility-helper" className="mt-1 block text-sm text-neutral-500">
									You can hide your profile while keeping recommendations active.
								</span>
							</span>
						</label>

						<label className="flex cursor-pointer items-start gap-3 rounded-md border border-neutral-200 bg-white p-4">
							<Checkbox
								checked={onboardingCompleted}
								onChange={(event) => setOnboardingCompleted(event.target.checked)}
								aria-describedby="completion-helper"
							/>
							<span>
								<span className="font-medium text-neutral-900">Onboarding completed</span>
								<span id="completion-helper" className="mt-1 block text-sm text-neutral-500">
									Marks your profile as ready for personalized opportunity browsing.
								</span>
							</span>
						</label>

						<div className="rounded-md border border-dashed border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-500">
							<span className="flex items-center gap-2 font-medium text-neutral-700">
								<Sparkles className="h-4 w-4" aria-hidden="true" />
								Recommendation settings
							</span>
							<span className="mt-1 block">
								Future controls for match tuning will live here once recommendation work begins.
							</span>
						</div>
					</ProfileSection>

					<div className="sticky bottom-0 z-20 -mx-4 border-t border-neutral-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur sm:mx-0 sm:rounded-lg sm:border">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<p className="text-sm text-neutral-500">
								Changes are saved to your recommendation-ready profile.
							</p>
							<div className="flex items-center justify-end gap-3">
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
										'Save profile'
									)}
								</Button>
							</div>
						</div>
					</div>
				</form>
			</div>
		</div>
	);
};

export default Profile;
