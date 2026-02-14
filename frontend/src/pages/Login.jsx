import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import { Input } from '../components/ui/input.jsx';
import { Label } from '../components/ui/label.jsx';
import { Alert, AlertDescription } from '../components/ui/alert.jsx';
import { Briefcase, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';

const Login = () => {
	const { login, error: authError } = useAuth();
	const navigate = useNavigate();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [errors, setErrors] = useState({});
	const [formError, setFormError] = useState('');
	const [isLoading, setIsLoading] = useState(false);

	const validateForm = () => {
		const newErrors = {};

		// Email validation
		if (!email.trim()) {
			newErrors.email = 'Email is required';
		} else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
			newErrors.email = 'Please enter a valid email address';
		}

		// Password validation
		if (!password) {
			newErrors.password = 'Password is required';
		} else if (password.length < 6) {
			newErrors.password = 'Password must be at least 6 characters';
		}

		setErrors(newErrors);
		return Object.keys(newErrors).length === 0;
	};

	const handleSubmit = async (event) => {
		event.preventDefault();
		setFormError('');

		if (!validateForm()) {
			return;
		}

		setIsLoading(true);
		const result = await login(email, password);
		setIsLoading(false);

		if (result.success) {
			navigate('/opportunities');
		} else if (result.error) {
			setFormError(result.error);
		}
	};

	return (
		<div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-12">
			<div className="w-full max-w-md">
				<div className="mb-8 text-center">
					<Link to="/" className="mb-4 inline-flex items-center gap-2">
						<div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600">
							<Briefcase className="h-7 w-7 text-white" />
						</div>
					</Link>
					<h1 className="mb-2 text-2xl font-bold text-neutral-900">Welcome back</h1>
					<p className="text-neutral-600">Sign in to your BidWise account</p>
				</div>

				<div className="rounded-lg border border-neutral-200 bg-white p-8">
					<form onSubmit={handleSubmit} className="space-y-6">
						{(formError || authError) && (
							<Alert variant="destructive">
								<AlertDescription>{formError || authError}</AlertDescription>
							</Alert>
						)}

						<div className="space-y-2">
							<Label htmlFor="email">Email address</Label>
							<Input
								id="email"
								type="email"
								placeholder="you@example.com"
								value={email}
								onChange={(event) => {
									setEmail(event.target.value);
									if (errors.email) setErrors({ ...errors, email: '' });
								}}
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

						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<Label htmlFor="password">Password</Label>
								<Link to="/password-reset" className="text-sm text-blue-600 hover:text-blue-700">
									Forgot password?
								</Link>
							</div>
							<Input
								id="password"
								type="password"
								placeholder="Enter your password"
								value={password}
								onChange={(event) => {
									setPassword(event.target.value);
									if (errors.password) setErrors({ ...errors, password: '' });
								}}
								disabled={isLoading}
								autoComplete="current-password"
								aria-invalid={errors.password ? 'true' : 'false'}
								aria-describedby={errors.password ? 'password-error' : undefined}
							/>
							{errors.password && (
								<p id="password-error" className="text-sm text-red-600">
									{errors.password}
								</p>
							)}
						</div>

						<Button type="submit" className="w-full" disabled={isLoading}>
							{isLoading ? (
								<>
									<Loader2 className="mr-2 h-4 w-4 animate-spin" />
									Logging in...
								</>
							) : (
								'Log in'
							)}
						</Button>
					</form>
				</div>

				<p className="mt-6 text-center text-neutral-600">
					Don't have an account?{' '}
					<Link to="/register" className="font-medium text-blue-600 hover:text-blue-700">
						Create an account
					</Link>
				</p>
			</div>
		</div>
	);
};

export default Login;
