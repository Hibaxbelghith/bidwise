import { useEffect, useState } from 'react';
import { Eye, EyeOff, LockKeyhole, LogIn, Mail, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Alert, AlertDescription } from '../../components/ui/alert.jsx';
import { Button } from '../../components/ui/button.jsx';
import { Input } from '../../components/ui/input.jsx';
import { Label } from '../../components/ui/label.jsx';
import LanguageToggle from '../../components/layout/LanguageToggle.jsx';
import { useLanguage } from '../../i18n/LanguageContext.jsx';
import { adminLogin, validateAdminSession } from './adminAuthService.js';
import { hasAdminSession, removeAdminTokens } from './adminTokenManager.js';

const AdminLoginPage = () => {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(() => hasAdminSession());

  const BRAND_LOGO_SRC = '/BidWise Icon.png';

  useEffect(() => {
    let isMounted = true;

    const redirectIfAlreadyAdmin = async () => {
      if (!hasAdminSession()) {
        setIsCheckingSession(false);
        return;
      }

      try {
        await validateAdminSession();
        if (isMounted) {
          navigate('/admin/dashboard', { replace: true });
        }
      } catch {
        removeAdminTokens();
        if (isMounted) {
          setIsCheckingSession(false);
        }
      }
    };

    redirectIfAlreadyAdmin();

    return () => {
      isMounted = false;
    };
  }, [navigate]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await adminLogin({ email, password });
      navigate('/admin/dashboard', { replace: true });
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isCheckingSession) {
    return null;
  }

  return (
    <section className="flex min-h-screen items-center justify-center bg-neutral-950 px-4 py-10">
      <div className="absolute right-4 top-4">
        <LanguageToggle />
      </div>
      <div className="w-full max-w-md rounded-lg border border-neutral-800 bg-white p-6 shadow-xl sm:p-8">
        <div className="mb-8">
          <div className="inline-flex">
            <img
              src={BRAND_LOGO_SRC}
              alt="BidWise"
              className="mx-auto  h-16 w-16 object-contain"
            />
          </div>
          <h1 className="text-2xl font-bold text-neutral-950">{t('admin.adminLogin')}</h1>
          <p className="mt-2 text-sm text-neutral-600">
            {t('admin.signInHelp')}
          </p>
        </div>

        {error ? (
          <Alert variant="destructive" className="mb-5">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="admin-email">Email</Label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" aria-hidden="true" />
              <Input
                id="admin-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="pl-9"
                autoComplete="email"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="admin-password">Password</Label>
            <div className="relative">
              <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" aria-hidden="true" />
              <Input
                id="admin-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="px-9"
                autoComplete="current-password"
                required
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-9 w-9 text-neutral-500 hover:text-neutral-900"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Eye className="h-4 w-4" aria-hidden="true" />
                )}
              </Button>
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            <LogIn className="h-4 w-4" aria-hidden="true" />
            {isSubmitting ? 'Signing in' : t('common.signIn')}
          </Button>
        </form>
      </div>
    </section>
  );
};

export default AdminLoginPage;
