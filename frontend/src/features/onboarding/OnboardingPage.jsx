import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { Button } from '../../components/ui/button.jsx';
import { Briefcase, ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { Spinner } from '../../components/ui/spinner.jsx';

import StepOpportunityIntent from './steps/StepOpportunityIntent.jsx';
import StepLocation from './steps/StepLocation.jsx';
import StepSkills from './steps/StepSkills.jsx';
import StepSalary from './steps/StepSalary.jsx';
import StepEmploymentType from './steps/StepEmploymentType.jsx';
import StepTargetRoles from './steps/StepTargetRoles.jsx';
import StepVisibility from './steps/StepVisibility.jsx';
import { normalizeProfilePreferenceData } from '../profile/profilePreferences.js';
import {
	DEFAULT_COMPENSATION_PERIOD,
	validateSalaryRange,
} from '../profile/profileValidation.js';
import {
	ORGANIZATION_CREATE_ACCOUNT_PATH,
	ORGANIZATION_DASHBOARD_PATH,
	isOrganizationAccount,
	isOrganizationProfileComplete,
} from '../organization/organizationFlow.js';

const TOTAL_STEPS = 7;
const STORAGE_KEY = 'bidwise_onboarding';
const USER_PROFILE_STORAGE_KEY = 'bidwise_user_profile';

const STEPS = [
	StepOpportunityIntent,
	StepLocation,
	StepSkills,
	StepSalary,
	StepEmploymentType,
	StepTargetRoles,
	StepVisibility,
];

const STEP_META = [
	{
		title: 'What brings you to BidWise?',
		subtitle:
			'Select the type of opportunities you are looking for. This helps us personalize your experience.',
	},
	{
		title: 'Where would you like to work?',
		subtitle: 'Location is required for on-site or hybrid work, and optional for remote.',
	},
	{
		title: 'Add your key skills',
		subtitle: 'Skills power your AI match score.',
	},
	{
		title: 'Expected salary range',
		subtitle: 'Share an optional TND/month range so matches are less brittle.',
	},
	{
		title: 'What type of work arrangement do you prefer?',
		subtitle: 'You can select multiple options.',
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
	profile_visibility: true,
};

const buildStoredProfileData = (data, onboardingCompleted = false) => ({
	...normalizeProfilePreferenceData(data),
	onboarding_completed: Boolean(onboardingCompleted),
});

const getStepValidationError = (step, data) => {
	if (step === 0 && (!Array.isArray(data.opportunity_types) || data.opportunity_types.length === 0)) {
		return 'Select at least one opportunity type to help us recommend relevant matches.';
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
		return 'Skills power your AI match score.';
	}

	if (step === 3) {
		return validateSalaryRange(
			data.compensation_min_expectation,
			data.compensation_max_expectation,
			data.compensation_period || DEFAULT_COMPENSATION_PERIOD
		).error;
	}

	if (step === 5 && (!Array.isArray(data.target_roles) || data.target_roles.length === 0)) {
		return 'Add at least one target role to guide your recommendations.';
	}

	return '';
};

const findFirstIncompleteRequiredStep = (data) => {
	for (const step of [0, 1, 2, 3, 5]) {
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
		/* corrupted storage — ignore */
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

	// Already onboarded → redirect to opportunities
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
		if (user?.profil?.onboarding_completed) {
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
		setData((prev) => ({ ...prev, [field]: value }));
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
		if (currentStep === TOTAL_STEPS - 1) {
			handleFinish();
		} else {
			setCurrentStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
		}
	};

	const handleBack = () => {
		setValidationError('');
		setCurrentStep((s) => Math.max(s - 1, 0));
	};

	const handleFinish = async () => {
		const incompleteStep = findFirstIncompleteRequiredStep(data);
		if (incompleteStep) {
			setCurrentStep(incompleteStep.step);
			setValidationError(incompleteStep.error);
			return;
		}

		setValidationError('');
		setSubmissionError(null);
		setIsSubmitting(true);
		try {
			const payload = {
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
					JSON.stringify(buildStoredProfileData(data, true))
				);
				sessionStorage.removeItem(STORAGE_KEY);
				navigate('/opportunities', { replace: true });
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
			const result = await updateUserProfile({
				...normalizeProfilePreferenceData(data),
				onboarding_completed: false,
				last_onboarding_step: currentStep,
			});
			if (result.success) {
				localStorage.setItem(
					USER_PROFILE_STORAGE_KEY,
					JSON.stringify(buildStoredProfileData(data, false))
				);
				sessionStorage.removeItem(STORAGE_KEY);
				navigate('/opportunities', { replace: true });
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
	const progress = Math.round(((currentStep + 1) / TOTAL_STEPS) * 100);
	const isLastStep = currentStep === TOTAL_STEPS - 1;

	return (
		<section className="flex min-h-screen items-start justify-center bg-neutral-50 px-4 py-12" aria-labelledby="onboarding-heading">
			<div className="w-full max-w-xl">
				{/* Logo */}
				<div className="mb-8 text-center">
					<Link to="/" className="inline-flex items-center gap-2" aria-label="BidWise home">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
							<Briefcase className="h-6 w-6 text-white" aria-hidden="true" />
						</div>
						<span className="text-xl font-semibold text-neutral-900">
							BidWise
						</span>
					</Link>
				</div>

				{/* Card */}
				<div className="rounded-lg border border-neutral-200 bg-white shadow-sm">
					{/* Progress bar */}
					<div className="border-b border-neutral-100 px-8 pt-6 pb-4">
						<div className="mb-2 flex items-center justify-between text-sm text-neutral-500">
							<span>
								Step {currentStep + 1} of {TOTAL_STEPS}
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
										Saving…
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
