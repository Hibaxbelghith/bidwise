import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { Button } from '../../components/ui/button.jsx';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { Spinner } from '../../components/ui/spinner.jsx';

import StepOpportunityIntent from './steps/StepOpportunityIntent.jsx';
import StepLocation from './steps/StepLocation.jsx';
import StepSkills from './steps/StepSkills.jsx';
import StepSectors from './steps/StepSectors.jsx';
import StepSalary from './steps/StepSalary.jsx';
import StepEmploymentType from './steps/StepEmploymentType.jsx';
import StepTargetRoles from './steps/StepTargetRoles.jsx';
import StepVisibility from './steps/StepVisibility.jsx';
import StepTenderPreferences from './steps/StepTenderPreferences.jsx';
import {
	getEmploymentTypeOptionsForOpportunityTypes,
	normalizeProfilePreferenceData,
} from '../profile/profilePreferences.js';
import {
	DEFAULT_COMPENSATION_PERIOD,
	validateSalaryRange,
} from '../profile/profileValidation.js';
import {
	ORGANIZATION_CREATE_ACCOUNT_PATH,
	ORGANIZATION_DASHBOARD_PATH,
	isOrganizationAccount,
	isOrganizationProfileComplete,
	shouldStartCandidateOnboarding,
} from '../organization/organizationFlow.js';

const STORAGE_KEY = 'bidwise_onboarding';
const USER_PROFILE_STORAGE_KEY = 'bidwise_user_profile';
const BRAND_LOGO_SRC = '/BidWise Icon.png';

const STEPS = [
	StepOpportunityIntent,
	StepLocation,
	StepSkills,
	StepSectors,
	StepSalary,
	StepEmploymentType,
	StepTargetRoles,
	StepVisibility,
	StepTenderPreferences,
];

const TOTAL_STEPS = STEPS.length;
const TENDER_PREFERENCES_STEP = TOTAL_STEPS - 1;

const STEP_META = [
	{
		title: 'What brings you to BidWise?',
		subtitle:
			'',
	},
	{
		title: 'Where would you like to work?',
		subtitle: '',
	},
	{
		title: 'Add your key skills',
		subtitle: 'Skills power your AI match score.',
	},
	{
		title: 'Choose your sectors',
		subtitle: 'Select the professional domains that best describe your profile.',
	},
	{
		title: 'Expected salary range',
		subtitle: 'Share an optional TND/month range so matches are less brittle.',
	},
	{
		title: 'What contract types are you open to?',
		subtitle: 'Select the employment contracts you would consider.',
	},
	{
		title: 'What roles are you targeting?',
		subtitle: 'This improves our recommendation engine.',
	},
	{
		title: 'Profile visibility',
		subtitle:
			'Control how your profile appears to recruiters. You can change this anytime in settings.',
	},
	{
		title: 'What tender categories interest you?',
		subtitle: 'Choose a controlled category so BidWise can prioritize relevant active tenders.',
	},
];

const initialData = {
	opportunity_types: [],
	preferred_locations: [],
	work_mode_preferences: [],
	compensation_expectation: null,
	compensation_min_expectation: null,
	compensation_max_expectation: null,
	compensation_currency: 'TND',
	compensation_period: DEFAULT_COMPENSATION_PERIOD,
	employment_types: [],
	target_roles: [],
	competences: [],
	domaines_interet: [],
	tender_preferences: { categories: [], max_budget: null },
	profile_visibility: true,
};

const isCallsForTenderOnly = (value) =>
	Array.isArray(value) &&
	value.length === 1 &&
	value[0] === 'CALLS_FOR_TENDER';

const buildTenderOnlyPayload = (data) => ({
	opportunity_types: ['CALLS_FOR_TENDER'],
	preferred_locations: data.preferred_locations || [],
	tender_preferences: data.tender_preferences || { categories: [], max_budget: null },
	onboarding_completed: true,
	last_onboarding_step: TENDER_PREFERENCES_STEP,
});

const buildStoredProfileData = (data, onboardingCompleted = false) => ({
	...normalizeProfilePreferenceData(data),
	onboarding_completed: Boolean(onboardingCompleted),
});

const buildDeferredOnboardingPayload = (data, currentStep) => {
	const normalized = normalizeProfilePreferenceData(data);

	return Object.fromEntries(
		Object.entries({
			...normalized,
			onboarding_completed: false,
			last_onboarding_step: currentStep,
		}).filter(([key, value]) => {
			if (key === 'onboarding_completed' || key === 'last_onboarding_step') {
				return true;
			}
			if (Array.isArray(value)) return value.length > 0;
			if (value === '' || value == null) return false;
			return true;
		})
	);
};

const getStepValidationError = (step, data) => {
	if (step === 0 && (!Array.isArray(data.opportunity_types) || data.opportunity_types.length === 0)) {
		return 'Select at least one opportunity type to help us recommend relevant matches.';
	}

	if (isCallsForTenderOnly(data.opportunity_types)) {
		if (step === 1 && (!Array.isArray(data.preferred_locations) || data.preferred_locations.length === 0)) {
			return 'Choose at least one region of interest.';
		}
		if (step === TENDER_PREFERENCES_STEP) {
			const firstCategory = Array.isArray(data.tender_preferences?.categories)
				? data.tender_preferences.categories[0]
				: null;
			if (!firstCategory?.category) {
				return 'Select a tender category.';
			}
			if (firstCategory.category !== 'Autre' && !firstCategory.subcategory) {
				return 'Select a tender subcategory.';
			}
			const maxBudget = data.tender_preferences?.max_budget;
			if (maxBudget !== null && maxBudget !== '' && Number(maxBudget) < 0) {
				return 'Enter a positive maximum budget.';
			}
		}
		return '';
	}

	if (step === 1 && (!Array.isArray(data.work_mode_preferences) || data.work_mode_preferences.length === 0)) {
		return 'Select at least one work mode preference so we can tailor your recommendations.';
	}

	if (
		step === 1 &&
		Array.isArray(data.work_mode_preferences) &&
		data.work_mode_preferences.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID') &&
		(!Array.isArray(data.preferred_locations) || data.preferred_locations.length === 0)
	) {
		return 'Choose at least one location for on-site or hybrid work.';
	}

	if (step === 2 && (!Array.isArray(data.competences) || data.competences.length === 0)) {
		return 'Add at least one skill.';
	}

	if (step === 3 && (!Array.isArray(data.domaines_interet) || data.domaines_interet.length === 0)) {
		return 'Choose at least one sector.';
	}

	if (step === 4) {
		return validateSalaryRange(
			data.compensation_min_expectation,
			data.compensation_max_expectation,
			data.compensation_period || DEFAULT_COMPENSATION_PERIOD
		).error;
	}

	if (step === 5 && (!Array.isArray(data.employment_types) || data.employment_types.length === 0)) {
		return 'Select at least one employment type.';
	}

	if (step === 6 && (!Array.isArray(data.target_roles) || data.target_roles.length === 0)) {
		return 'Add at least one target role.';
	}

	return '';
};

const findFirstIncompleteRequiredStep = (data) => {
	if (isCallsForTenderOnly(data.opportunity_types)) {
		for (const step of [0, 1, TENDER_PREFERENCES_STEP]) {
			const error = getStepValidationError(step, data);
			if (error) return { step, error };
		}
		return null;
	}
	for (const step of [0, 1, 2, 3, 4, 5, 6]) {
		const error = getStepValidationError(step, data);
		if (error) {
			return { step, error };
		}
	}

	return null;
};

function loadSavedState() {
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (raw) {
			const parsed = JSON.parse(raw);
			return {
				step: typeof parsed.step === 'number' ? parsed.step : 0,
				data: {
					...initialData,
					...normalizeProfilePreferenceData(parsed.data || {}),
				},
			};
		}
	} catch {
		/* corrupted storage - ignore */
	}
	return null;
}

const Onboarding = () => {
	const navigate = useNavigate();
	const { user, loading, updateUserProfile } = useAuth();

	const saved = loadSavedState();
	const [currentStep, setCurrentStep] = useState(saved?.step ?? 0);
	const [data, setData] = useState(saved?.data ?? { ...initialData });
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [validationError, setValidationError] = useState('');
	const [submissionError, setSubmissionError] = useState(null);
	const headingRef = useRef(null);

	// Already onboarded - redirect to opportunities
	useEffect(() => {
		if (loading) return;
		if (isOrganizationAccount(user)) {
			navigate(
				isOrganizationProfileComplete(user?.organization_profile)
					? ORGANIZATION_DASHBOARD_PATH
					: ORGANIZATION_CREATE_ACCOUNT_PATH,
				{ replace: true },
			);
			return;
		}
		if (!shouldStartCandidateOnboarding(user)) {
			navigate('/opportunities', { replace: true });
		}
	}, [user, loading, navigate]);

	// Focus heading when step changes for screen readers
	useEffect(() => {
		if (headingRef.current) headingRef.current.focus();
	}, [currentStep]);

	// Persist to sessionStorage on every change
	useEffect(() => {
		sessionStorage.setItem(
			STORAGE_KEY,
			JSON.stringify({ step: currentStep, data })
		);
	}, [currentStep, data]);

	const handleChange = (field, value) => {
		setData((prev) => {
			const next = { ...prev, [field]: value };
			if (field === 'opportunity_types') {
				const allowed = new Set(
					getEmploymentTypeOptionsForOpportunityTypes(value).map((option) => option.value)
				);
				next.employment_types = (prev.employment_types || []).filter((item) => allowed.has(item));
				if (isCallsForTenderOnly(value)) {
					next.work_mode_preferences = [];
					next.employment_types = [];
					next.target_roles = [];
					next.competences = [];
					next.domaines_interet = [];
				}
			}
			return next;
		});
		setValidationError('');
	};

	const handleNext = () => {
		const stepError = getStepValidationError(currentStep, data);
		if (stepError) {
			setValidationError(stepError);
			return;
		}
		setValidationError('');
		setSubmissionError(null);
		if (currentStep === 0 && isCallsForTenderOnly(data.opportunity_types)) {
			setCurrentStep(1);
			return;
		}
		if (currentStep === 1 && isCallsForTenderOnly(data.opportunity_types)) {
			setCurrentStep(TENDER_PREFERENCES_STEP);
			return;
		}
		if (currentStep === TENDER_PREFERENCES_STEP || (!isCallsForTenderOnly(data.opportunity_types) && currentStep === TOTAL_STEPS - 2)) {
			handleFinish();
		} else {
			setCurrentStep((s) => Math.min(s + 1, TOTAL_STEPS - 2));
		}
	};

	const handleBack = () => {
		setValidationError('');
		setCurrentStep((s) => {
			if (s === TENDER_PREFERENCES_STEP && isCallsForTenderOnly(data.opportunity_types)) return 1;
			return Math.max(s - 1, 0);
		});
	};

	const handleFinish = async () => {
		const tenderOnly = isCallsForTenderOnly(data.opportunity_types);
		const incompleteStep = tenderOnly ? null : findFirstIncompleteRequiredStep(data);
		if (incompleteStep) {
			setCurrentStep(incompleteStep.step);
			setValidationError(incompleteStep.error);
			return;
		}

		setValidationError('');
		setSubmissionError(null);
		setIsSubmitting(true);
		try {
			const payload = tenderOnly
				? buildTenderOnlyPayload(data)
				: {
					...normalizeProfilePreferenceData(data),
					compensation_expectation:
						data.compensation_min_expectation ?? data.compensation_max_expectation ?? null,
					onboarding_completed: true,
					last_onboarding_step: currentStep,
				};
			const result = await updateUserProfile(payload);
			if (result.success) {
				localStorage.setItem(
					USER_PROFILE_STORAGE_KEY,
					JSON.stringify(buildStoredProfileData(tenderOnly ? payload : data, true))
				);
				sessionStorage.removeItem(STORAGE_KEY);
				navigate(tenderOnly ? '/opportunities?type=PROJET' : '/opportunities', { replace: true });
			} else {
				setSubmissionError(result.error || 'Failed to save profile');
			}
		} catch (err) {
			setSubmissionError(err.message || 'Failed to save profile');
		} finally {
			setIsSubmitting(false);
		}
	};

	const handleSkip = async () => {
		setValidationError('');
		setSubmissionError(null);
		setIsSubmitting(true);
		try {
			const result = await updateUserProfile(buildDeferredOnboardingPayload(data, currentStep));
			if (result.success) {
				localStorage.setItem(
					USER_PROFILE_STORAGE_KEY,
					JSON.stringify(buildStoredProfileData(data, false))
				);
				sessionStorage.removeItem(STORAGE_KEY);
				navigate('/opportunities?tab=explore', { replace: true });
			} else {
				setSubmissionError(result.error || 'Failed to save profile');
			}
		} catch (err) {
			setSubmissionError(err.message || 'Failed to save profile');
		} finally {
			setIsSubmitting(false);
		}
	};

	// Show nothing while loading auth
	if (loading) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-neutral-50">
				   <Spinner size={32} color="#2563eb" />
			</div>
		);
	}

	const StepComponent = STEPS[currentStep];
	const meta = STEP_META[currentStep];
	const tenderOnly = isCallsForTenderOnly(data.opportunity_types);
	const tenderProgressMap = { 0: 33, 1: 66, [TENDER_PREFERENCES_STEP]: 100 };
	const progress = tenderOnly
		? (tenderProgressMap[currentStep] || 33)
		: Math.round(((currentStep + 1) / (TOTAL_STEPS - 1)) * 100);
	const isLastStep = tenderOnly ? currentStep === TENDER_PREFERENCES_STEP : currentStep === TOTAL_STEPS - 2;

	return (
		<section className="flex min-h-screen items-start justify-center bg-neutral-50 px-4 py-12" aria-labelledby="onboarding-heading">
			<div className="w-full max-w-xl">
				{/* Logo */}
				<div className="mb-8 text-center">
					<Link to="/" className="inline-flex items-center gap-1" aria-label="BidWise home">
						<img src={BRAND_LOGO_SRC} alt="BidWise" className="h-20 w-20 object-contain" />
					</Link>
				</div>

				{/* Card */}
				<div className="rounded-lg border border-neutral-200 bg-white shadow-sm">
					{/* Progress bar */}
					<div className="border-b border-neutral-100 px-8 pt-6 pb-4">
						<div className="mb-2 flex items-center justify-between text-sm text-neutral-500">
							<span>
								Step {tenderOnly ? (currentStep === TENDER_PREFERENCES_STEP ? 3 : currentStep + 1) : currentStep + 1} of {tenderOnly ? 3 : TOTAL_STEPS - 1}
							</span>
							<span>{progress}%</span>
						</div>
						<div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label={`Onboarding progress: ${progress}%`}>
							<div
								className="h-full rounded-full bg-blue-600 transition-all duration-300"
								style={{ width: `${progress}%` }}
							/>
						</div>
					</div>

					{/* Step header */}
					<div className="px-8 pt-6">
						<h1 id="onboarding-heading" ref={headingRef} tabIndex={-1} className="text-xl font-semibold text-neutral-900">
							{meta.title}
						</h1>
						<p className="mt-1 text-sm text-neutral-500">
							{meta.subtitle}
						</p>
					</div>

					{/* Step content */}
					<div className="px-8 py-6">
						<StepComponent data={data} onChange={handleChange} error={validationError} />
					</div>

					{/* Error */}
					{submissionError && (
						<div className="px-8 pb-2" role="alert" aria-live="assertive">
							<p className="text-sm text-red-600">{submissionError}</p>
						</div>
					)}

					{/* Navigation */}
					<div className="flex items-center justify-between border-t border-neutral-100 px-8 py-4">
						<div>
							{currentStep > 0 && (
								<Button
									variant="ghost"
									onClick={handleBack}
									disabled={isSubmitting}
								>
								<ArrowLeft className="mr-1 h-4 w-4" aria-hidden="true" />
									Back
								</Button>
							)}
						</div>

						<div className="flex items-center gap-2">
							<Button
								variant="ghost"
								className="text-neutral-500"
								onClick={handleSkip}
								disabled={isSubmitting}
							>
								Skip for now
							</Button>

							<Button onClick={handleNext} disabled={isSubmitting}>
								{isSubmitting ? (
									<>
										   <Spinner size={18} className="mr-2" />
										Saving...
									</>
								) : isLastStep ? (
									<>
										<Check className="mr-1 h-4 w-4" aria-hidden="true" />
										Finish
									</>
								) : (
									<>
										Next
										<ArrowRight className="ml-1 h-4 w-4" aria-hidden="true" />
									</>
								)}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</section>
	);
};

export default Onboarding;
