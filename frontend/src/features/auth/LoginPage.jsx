import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button.jsx';
import { Input } from '../../components/ui/input.jsx';
import { Label } from '../../components/ui/label.jsx';
import { Alert, AlertDescription } from '../../components/ui/alert.jsx';
import { Briefcase, Loader2, ArrowLeft, Mail, CheckCircle2 } from 'lucide-react';
import { useAuth } from './AuthContext.jsx';
import { useGoogleIdentity } from './useGoogleIdentity.js';

const COOLDOWN_SECONDS = 60;
const VITE_GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

const OTPLogin = () => {
	const { requestOTP, verifyOTP, loginWithGoogle, error: authError, isAuthenticated } = useAuth();
	const navigate = useNavigate();

	// Google login
	const [googleError, setGoogleError] = useState('');
	const [googleLoading, setGoogleLoading] = useState(false);


	const handleGoogleSuccess = async (idToken) => {
		setFormError('');
		setGoogleError('');
		setGoogleLoading(true);

		const result = await loginWithGoogle(idToken);
		setGoogleLoading(false);

		if (result.success) {
			if (result.is_new_user) {
				navigate('/onboarding', { replace: true });
			} else {
				navigate('/dashboard', { replace: true });
			}
		} else {
			setGoogleError(result.error);
		}
	};

	const handleGoogleError = (msg) => {
		setGoogleError(msg);
	};

	const { containerRef: googleBtnRef, ready: googleReady } = useGoogleIdentity(
		handleGoogleSuccess,
		handleGoogleError,
	);

	// Step 1 = email, Step 2 = OTP verification
	const [step, setStep] = useState(1);
	const [email, setEmail] = useState('');
	const [otp, setOtp] = useState('');
	const [emailError, setEmailError] = useState('');
	const [otpError, setOtpError] = useState('');
	const [formError, setFormError] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const [cooldown, setCooldown] = useState(0);

	// Redirect if already authenticated
	useEffect(() => {
		if (isAuthenticated) {
			navigate('/dashboard', { replace: true });
		}
	}, [isAuthenticated, navigate]);

	// Cooldown timer
	useEffect(() => {
		if (cooldown <= 0) return;
		const timer = setInterval(() => {
			setCooldown((prev) => (prev <= 1 ? 0 : prev - 1));
		}, 1000);
		return () => clearInterval(timer);
	}, [cooldown]);

	// ── Step 1: Request OTP ─────────────────────────────────

	const validateEmail = () => {
		if (!email.trim()) {
			setEmailError('Email is required');
			return false;
		}
		if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
			setEmailError('Please enter a valid email address');
			return false;
		}
		setEmailError('');
		return true;
	};

	const handleRequestOTP = async (event) => {
		event.preventDefault();
		setFormError('');

		if (!validateEmail()) return;

		setIsLoading(true);
		const result = await requestOTP(email);
		setIsLoading(false);

		if (result.success) {
			setStep(2);
			setCooldown(COOLDOWN_SECONDS);
		} else {
			setFormError(result.error);
		}
	};

	// ── Step 2: Verify OTP ──────────────────────────────────

	const validateOTP = () => {
		if (!otp.trim()) {
			setOtpError('Code is required');
			return false;
		}
		if (!/^\d{6}$/.test(otp.trim())) {
			setOtpError('Please enter a valid 6-digit code');
			return false;
		}
		setOtpError('');
		return true;
	};

	const handleVerifyOTP = async (event) => {
		event.preventDefault();
		setFormError('');

		if (!validateOTP()) return;

		setIsLoading(true);
		const result = await verifyOTP(email, otp.trim());
		setIsLoading(false);

		if (result.success) {
			if (result.is_new_user) {
				navigate('/onboarding', { replace: true });
			} else {
				navigate('/dashboard', { replace: true });
			}
		} else {
			setFormError(result.error);
		}
	};

	// ── Resend OTP ──────────────────────────────────────────

	const handleResend = useCallback(async () => {
		if (cooldown > 0) return;
		setFormError('');
		setOtp('');
		setOtpError('');

		setIsLoading(true);
		const result = await requestOTP(email);
		setIsLoading(false);

		if (result.success) {
			setCooldown(COOLDOWN_SECONDS);
		} else {
			setFormError(result.error);
		}
	}, [cooldown, email, requestOTP]);

	// ── Go back to step 1 ───────────────────────────────────

	const handleBack = () => {
		setStep(1);
		setOtp('');
		setOtpError('');
		setFormError('');
		setCooldown(0);
	};

	// ── Render ──────────────────────────────────────────────

	return (
		<div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-12">
			<div className="w-full max-w-md">
				{/* Header */}
				<div className="mb-8 text-center">
					<Link to="/" className="mb-4 inline-flex items-center gap-2">
						<div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600">
							<Briefcase className="h-7 w-7 text-white" />
						</div>
					</Link>
					{step === 1 ? (
						<>
							<h1 className="mb-2 text-2xl font-bold text-neutral-900">Sign in to BidWise</h1>
							<p className="text-neutral-600">
								Enter your email to receive a login code
							</p>
						</>
					) : (
						<>
							<h1 className="mb-2 text-2xl font-bold text-neutral-900">Enter your code</h1>
							<p className="text-neutral-600">
								We sent a 6-digit code to{' '}
								<span className="font-medium text-neutral-900">{email}</span>
							</p>
						</>
					)}
				</div>

				{/* Card */}
				<div className="rounded-lg border border-neutral-200 bg-white p-8">
					{/* ── Step 1: Email ── */}
					{step === 1 && (
						<form onSubmit={handleRequestOTP} className="space-y-6">
							{(formError || authError || googleError) && (
								<Alert variant="destructive">
									<AlertDescription>{formError || authError || googleError}</AlertDescription>
								</Alert>
							)}

							{/* Google button */}
							{googleReady && (
								<>
									<div className="relative">
										<div
											ref={googleBtnRef}
											className={googleLoading ? 'pointer-events-none opacity-50' : ''}
										/>
									</div>

									{/* Separator */}
									<div className="relative flex items-center">
										<div className="flex-grow border-t border-neutral-200" />
										<span className="mx-3 shrink-0 text-xs text-neutral-400">or</span>
										<div className="flex-grow border-t border-neutral-200" />
									</div>
								</>
							)}

							<div className="space-y-2">
								<Label htmlFor="email">Email address</Label>
								<Input
									id="email"
									type="email"
									placeholder="you@example.com"
									value={email}
									onChange={(e) => {
										setEmail(e.target.value);
										if (emailError) setEmailError('');
									}}
									disabled={isLoading}
									autoComplete="email"
									autoFocus
									aria-invalid={emailError ? 'true' : 'false'}
									aria-describedby={emailError ? 'email-error' : undefined}
								/>
								{emailError && (
									<p id="email-error" className="text-sm text-red-600">
										{emailError}
									</p>
								)}
							</div>

							<Button type="submit" className="w-full" disabled={isLoading}>
								{isLoading ? (
									<>
										<Loader2 className="mr-2 h-4 w-4 animate-spin" />
										Sending code...
									</>
								) : (
									<>
										<Mail className="mr-2 h-4 w-4" />
										Send Code
									</>
								)}
							</Button>
						</form>
					)}

					{/* ── Step 2: OTP ── */}
					{step === 2 && (
						<form onSubmit={handleVerifyOTP} className="space-y-6">
							{/* Success banner */}
							<div className="flex items-center gap-2 rounded-md bg-green-50 p-3 text-sm text-green-800">
								<CheckCircle2 className="h-4 w-4 flex-shrink-0 text-green-600" />
								Code sent to your email
							</div>

							{(formError || authError) && (
								<Alert variant="destructive">
									<AlertDescription>{formError || authError}</AlertDescription>
								</Alert>
							)}

							<div className="space-y-2">
								<Label htmlFor="otp">6-digit code</Label>
								<Input
									id="otp"
									type="text"
									inputMode="numeric"
									placeholder="000000"
									maxLength={6}
									value={otp}
									onChange={(e) => {
										// Only allow digits
										const val = e.target.value.replace(/\D/g, '');
										setOtp(val);
										if (otpError) setOtpError('');
									}}
									disabled={isLoading}
									autoComplete="one-time-code"
									autoFocus
									className="text-center text-2xl tracking-[0.5em]"
									aria-invalid={otpError ? 'true' : 'false'}
									aria-describedby={otpError ? 'otp-error' : undefined}
								/>
								{otpError && (
									<p id="otp-error" className="text-sm text-red-600">
										{otpError}
									</p>
								)}
							</div>

							<Button type="submit" className="w-full" disabled={isLoading}>
								{isLoading ? (
									<>
										<Loader2 className="mr-2 h-4 w-4 animate-spin" />
										Verifying...
									</>
								) : (
									'Verify & Sign In'
								)}
							</Button>

							{/* Resend + Back */}
							<div className="flex items-center justify-between text-sm">
								<button
									type="button"
									onClick={handleBack}
									className="flex items-center gap-1 text-neutral-600 hover:text-neutral-900"
								>
									<ArrowLeft className="h-3 w-3" />
									Change email
								</button>

								{cooldown > 0 ? (
									<span className="text-neutral-500">
										Resend in {cooldown}s
									</span>
								) : (
									<button
										type="button"
										onClick={handleResend}
										disabled={isLoading}
										className="font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50"
									>
										Resend code
									</button>
								)}
							</div>
						</form>
					)}
				</div>

				{/* Footer */}
				<p className="mt-6 text-center text-sm text-neutral-500">
					No password needed — we'll email you a login code every time.
				</p>
			</div>
		</div>
	);
};

export default OTPLogin;
