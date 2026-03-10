import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { Button } from '../../components/ui/button.jsx';
import { Briefcase, ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { Spinner } from '../../components/ui/spinner.jsx';

import StepOpportunityIntent from './steps/StepOpportunityIntent.jsx';
import StepLocation from './steps/StepLocation.jsx';
import StepSalary from './steps/StepSalary.jsx';
import StepEmploymentType from './steps/StepEmploymentType.jsx';
import StepTargetRoles from './steps/StepTargetRoles.jsx';
import StepVisibility from './steps/StepVisibility.jsx';

const TOTAL_STEPS = 6;
const STORAGE_KEY = 'bidwise_onboarding';

const STEPS = [
	StepOpportunityIntent,
	StepLocation,
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
		subtitle: 'We use this to match you with relevant opportunities.',
	},
	{
		title: 'Compensation expectations',
		subtitle:
			'This helps filter opportunities aligned with your expectations.',
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
	preferred_location: null,
	remote_preference: null,
	compensation_expectation: null,
	compensation_period: null,
	employment_types: [],
	target_roles: [],
	profile_visibility: true,
};

function loadSavedState() {
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (raw) {
			const parsed = JSON.parse(raw);
			return {
				step: typeof parsed.step === 'number' ? parsed.step : 0,
				data: { ...initialData, ...(parsed.data || {}) },
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
	const [error, setError] = useState(null);
	const headingRef = useRef(null);

	// Already onboarded → redirect to dashboard
	useEffect(() => {
		if (!loading && user?.profil?.onboarding_completed) {
			navigate('/dashboard', { replace: true });
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
	};

	const handleNext = () => {
		if (currentStep === TOTAL_STEPS - 1) {
			handleFinish();
		} else {
			setCurrentStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
		}
	};

	const handleBack = () => {
		setCurrentStep((s) => Math.max(s - 1, 0));
	};

	const handleFinish = async () => {
		setError(null);
		setIsSubmitting(true);
		try {
			const payload = {
				...data,
				onboarding_completed: true,
				last_onboarding_step: currentStep,
			};
			const result = await updateUserProfile(payload);
			if (result.success) {
				sessionStorage.removeItem(STORAGE_KEY);
				navigate('/dashboard', { replace: true });
			} else {
				setError(result.error || 'Failed to save profile');
			}
		} catch (err) {
			setError(err.message || 'Failed to save profile');
		} finally {
			setIsSubmitting(false);
		}
	};

	const handleSkip = async () => {
		setError(null);
		setIsSubmitting(true);
		try {
			const result = await updateUserProfile({
				onboarding_completed: true,
				last_onboarding_step: currentStep,
			});
			if (result.success) {
				sessionStorage.removeItem(STORAGE_KEY);
				navigate('/dashboard', { replace: true });
			} else {
				setError(result.error || 'Failed to save profile');
			}
		} catch (err) {
			setError(err.message || 'Failed to save profile');
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
						<StepComponent data={data} onChange={handleChange} />
					</div>

					{/* Error */}
					{error && (
						<div className="px-8 pb-2" role="alert" aria-live="assertive">
							<p className="text-sm text-red-600">{error}</p>
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
