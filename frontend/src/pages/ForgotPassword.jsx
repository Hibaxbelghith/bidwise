import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import { Input } from '../components/ui/input.jsx';
import { Label } from '../components/ui/label.jsx';
import { Alert, AlertDescription } from '../components/ui/alert.jsx';
import { ArrowLeft, Briefcase, CheckCircle2, Loader2, Mail } from 'lucide-react';
import { requestPasswordReset } from '../services/authService.js';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [formError, setFormError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');

    if (!email) {
      setFormError('Please enter your email address');
      return;
    }

    if (!email.includes('@')) {
      setFormError('Please enter a valid email address');
      return;
    }

    setIsLoading(true);
    try {
      await requestPasswordReset(email);
      setIsSuccess(true);
    } catch (error) {
      setFormError(error.message || 'Failed to send reset link');
    } finally {
      setIsLoading(false);
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
          {!isSuccess ? (
            <>
              <h1 className="mb-2 text-2xl font-bold text-neutral-900">Reset your password</h1>
              <p className="text-neutral-600">
                Enter your email address and we'll send you a link to reset your password
              </p>
            </>
          ) : (
            <>
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              </div>
              <h1 className="mb-2 text-2xl font-bold text-neutral-900">Check your email</h1>
              <p className="text-neutral-600">
                We've sent a password reset link to{' '}
                <span className="font-medium text-neutral-900">{email}</span>
              </p>
            </>
          )}
        </div>

        <div className="rounded-lg border border-neutral-200 bg-white p-8">
          {!isSuccess ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              {formError && (
                <Alert variant="destructive">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  disabled={isLoading}
                  autoComplete="email"
                  autoFocus
                  required
                />
              </div>

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Mail className="mr-2 h-4 w-4" />
                    Send reset link
                  </>
                )}
              </Button>
            </form>
          ) : (
            <div className="space-y-6">
              <div className="space-y-3 text-sm text-neutral-600">
                <p>Click the link in the email to create a new password.</p>
                <p>If you don't see the email, check your spam folder.</p>
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  setIsSuccess(false);
                  setEmail('');
                }}
              >
                Use a different email
              </Button>
            </div>
          )}
        </div>

        <div className="mt-6 text-center">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to login
          </Link>
        </div>

        {isSuccess && (
          <p className="mt-6 text-center text-sm text-neutral-600">
            Still need help?{' '}
            <a href="#" className="text-blue-600 hover:text-blue-700">
              Contact support
            </a>
          </p>
        )}
      </div>
    </div>
  );
};

export default ForgotPassword;
