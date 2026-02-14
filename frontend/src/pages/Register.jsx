import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import { Input } from '../components/ui/input.jsx';
import { Label } from '../components/ui/label.jsx';
import { Alert, AlertDescription } from '../components/ui/alert.jsx';
import { Briefcase, Building2, Loader2, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';

const Register = () => {
	const { register, error: authError } = useAuth();
	const navigate = useNavigate();
	const [accountType, setAccountType] = useState('CANDIDAT');
	const [formData, setFormData] = useState({
		first_name: '',
		last_name: '',
		email: '',
		password: '',
		password2: '',
	});
	const [errors, setErrors] = useState({});
	const [formError, setFormError] = useState('');
	const [isLoading, setIsLoading] = useState(false);

	const validateForm = () => {
		const newErrors = {};

		// Name validation
		if (!formData.first_name.trim()) {
			newErrors.first_name = 'First name is required';
		} else if (formData.first_name.trim().length < 2) {
			newErrors.first_name = 'First name must be at least 2 characters';
		}

		if (!formData.last_name.trim()) {
			newErrors.last_name = 'Last name is required';
		} else if (formData.last_name.trim().length < 2) {
			newErrors.last_name = 'Last name must be at least 2 characters';
		}

		// Email validation
		if (!formData.email.trim()) {
			newErrors.email = 'Email is required';
		} else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
			newErrors.email = 'Please enter a valid email address';
		}

		// Password validation
		if (!formData.password) {
			newErrors.password = 'Password is required';
		} else if (formData.password.length < 8) {
			newErrors.password = 'Password must be at least 8 characters';
		} else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
			newErrors.password = 'Password must contain uppercase, lowercase and number';
		}

		// Confirm password validation
		if (!formData.password2) {
			newErrors.password2 = 'Please confirm your password';
		} else if (formData.password !== formData.password2) {
			newErrors.password2 = 'Passwords do not match';
		}

		setErrors(newErrors);
		return Object.keys(newErrors).length === 0;
	};

	const handleChange = (field, value) => {
		setFormData((prev) => ({ ...prev, [field]: value }));
		if (errors[field]) {
			setErrors((prev) => ({ ...prev, [field]: '' }));
		}
	};

	const handleSubmit = async (event) => {
		event.preventDefault();
		setFormError('');

		if (!validateForm()) {
			return;
		}

		setIsLoading(true);
		const result = await register({
			...formData,
			account_type: accountType,
		});
		setIsLoading(false);

		if (result.success) {
			navigate('/login');
		} else if (result.error) {
			setFormError(result.error);
		}
	};

	return (
		<div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-12">
			<div className="w-full max-w-2xl">
				<div className="mb-8 text-center">
					<Link to="/" className="mb-4 inline-flex items-center gap-2">
						<div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600">
							<Briefcase className="h-7 w-7 text-white" />
						</div>
					</Link>
					<h1 className="mb-2 text-2xl font-bold text-neutral-900">Create your account</h1>
					<p className="text-neutral-600">Join BidWise to discover professional opportunities</p>
				</div>

				<div className="rounded-lg border border-neutral-200 bg-white p-8">
					<form onSubmit={handleSubmit} className="space-y-6">
						<div className="space-y-3">
							<Label>I am a...</Label>
							<div className="grid grid-cols-2 gap-4">
								<button
									type="button"
									onClick={() => setAccountType('CANDIDAT')}
									className={
										'relative flex flex-col items-center gap-3 rounded-lg border-2 p-6 transition-all ' +
										(accountType === 'CANDIDAT'
											? 'border-blue-600 bg-blue-50'
											: 'border-neutral-200 bg-white hover:border-neutral-300')
									}
								>
									<div
										className={
											'flex h-12 w-12 items-center justify-center rounded-lg ' +
											(accountType === 'CANDIDAT' ? 'bg-blue-600' : 'bg-neutral-100')
										}
									>
										<User className={accountType === 'CANDIDAT' ? 'h-6 w-6 text-white' : 'h-6 w-6 text-neutral-600'} />
									</div>
									<div className="text-center">
										<p className={accountType === 'CANDIDAT' ? 'font-semibold text-blue-600' : 'font-semibold text-neutral-900'}>
											Candidate
										</p>
										<p className="mt-1 text-sm text-neutral-600">Search and apply for opportunities</p>
									</div>
									{accountType === 'CANDIDAT' && (
										<div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-blue-600">
											<svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
											</svg>
										</div>
									)}
								</button>

								<button
									type="button"
									onClick={() => setAccountType('ORGANISATION')}
									className={
										'relative flex flex-col items-center gap-3 rounded-lg border-2 p-6 transition-all ' +
										(accountType === 'ORGANISATION'
											? 'border-blue-600 bg-blue-50'
											: 'border-neutral-200 bg-white hover:border-neutral-300')
									}
								>
									<div
										className={
											'flex h-12 w-12 items-center justify-center rounded-lg ' +
											(accountType === 'ORGANISATION' ? 'bg-blue-600' : 'bg-neutral-100')
										}
									>
										<Building2
											className={accountType === 'ORGANISATION' ? 'h-6 w-6 text-white' : 'h-6 w-6 text-neutral-600'}
										/>
									</div>
									<div className="text-center">
										<p className={
											accountType === 'ORGANISATION' ? 'font-semibold text-blue-600' : 'font-semibold text-neutral-900'
										}>
											Organization
										</p>
										<p className="mt-1 text-sm text-neutral-600">Post and manage opportunities</p>
									</div>
									{accountType === 'ORGANISATION' && (
										<div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-blue-600">
											<svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
											</svg>
										</div>
									)}
								</button>
							</div>
						</div>

						{(formError || authError) && (
							<Alert variant="destructive">
								<AlertDescription>{formError || authError}</AlertDescription>
							</Alert>
						)}

						<div className="grid gap-4 sm:grid-cols-2">
							<div className="space-y-2">
								<Label htmlFor="firstName">First name</Label>
								<Input
									id="firstName"
									type="text"
									placeholder="Enter your first name"
									value={formData.first_name}
									onChange={(event) => handleChange('first_name', event.target.value)}
									disabled={isLoading}
									autoComplete="given-name"
									aria-invalid={errors.first_name ? 'true' : 'false'}
									aria-describedby={errors.first_name ? 'first-name-error' : undefined}
								/>
								{errors.first_name && (
									<p id="first-name-error" className="text-sm text-red-600">
										{errors.first_name}
									</p>
								)}
							</div>

							<div className="space-y-2">
								<Label htmlFor="lastName">Last name</Label>
								<Input
									id="lastName"
									type="text"
									placeholder="Enter your last name"
									value={formData.last_name}
									onChange={(event) => handleChange('last_name', event.target.value)}
									disabled={isLoading}
									autoComplete="family-name"
									aria-invalid={errors.last_name ? 'true' : 'false'}
									aria-describedby={errors.last_name ? 'last-name-error' : undefined}
								/>
								{errors.last_name && (
									<p id="last-name-error" className="text-sm text-red-600">
										{errors.last_name}
									</p>
								)}
							</div>
						</div>

						<div className="space-y-2">
							<Label htmlFor="email">Email address</Label>
							<Input
								id="email"
								type="email"
								placeholder="you@example.com"
								value={formData.email}
								onChange={(event) => handleChange('email', event.target.value)}
								disabled={isLoading}
								autoComplete="email"
								aria-invalid={errors.email ? 'true' : 'false'}
								aria-describedby={errors.email ? 'email-error' : undefined}
							/>
							{errors.email && (
								<p id="email-error" className="text-sm text-red-600">
									{errors.email}
								</p>
							)}
						</div>

						<div className="grid gap-4 sm:grid-cols-2">
							<div className="space-y-2">
								<Label htmlFor="password">Password</Label>
								<Input
									id="password"
									type="password"
									placeholder="Min. 8 characters"
									value={formData.password}
									onChange={(event) => handleChange('password', event.target.value)}
									disabled={isLoading}
									autoComplete="new-password"
									aria-invalid={errors.password ? 'true' : 'false'}
									aria-describedby={errors.password ? 'password-error' : undefined}
								/>
								{errors.password && (
									<p id="password-error" className="text-sm text-red-600">
										{errors.password}
									</p>
								)}
								<p className="text-xs text-neutral-500">
									Must contain uppercase, lowercase and number
								</p>
							</div>

							<div className="space-y-2">
								<Label htmlFor="confirmPassword">Confirm password</Label>
								<Input
									id="confirmPassword"
									type="password"
									placeholder="Re-enter password"
									value={formData.password2}
									onChange={(event) => handleChange('password2', event.target.value)}
									disabled={isLoading}
									autoComplete="new-password"
									aria-invalid={errors.password2 ? 'true' : 'false'}
									aria-describedby={errors.password2 ? 'password2-error' : undefined}
								/>
								{errors.password2 && (
									<p id="password2-error" className="text-sm text-red-600">
										{errors.password2}
									</p>
								)}
							</div>
						</div>

						<p className="text-sm text-neutral-600">
							By creating an account, you agree to our{' '}
							<a href="#" className="text-blue-600 hover:text-blue-700">
								Terms of Service
							</a>{' '}
							and{' '}
							<a href="#" className="text-blue-600 hover:text-blue-700">
								Privacy Policy
							</a>
							.
						</p>

						<Button type="submit" className="w-full" disabled={isLoading}>
							{isLoading ? (
								<>
									<Loader2 className="mr-2 h-4 w-4 animate-spin" />
									Creating account...
								</>
							) : (
								'Create account'
							)}
						</Button>
					</form>
				</div>

				<p className="mt-6 text-center text-neutral-600">
					Already have an account?{' '}
					<Link to="/login" className="font-medium text-blue-600 hover:text-blue-700">
						Log in
					</Link>
				</p>
			</div>
		</div>
	);
};

export default Register;
