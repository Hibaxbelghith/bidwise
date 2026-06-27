import { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../../components/ui/button.jsx';
import { Input } from '../../components/ui/input.jsx';
import { Label } from '../../components/ui/label.jsx';
import { Alert, AlertDescription } from '../../components/ui/alert.jsx';
import { ArrowLeft, Mail, CheckCircle2 } from 'lucide-react';
import { Spinner } from '../../components/ui/spinner.jsx';
import LanguageToggle from '../../components/layout/LanguageToggle.jsx';
import { useLanguage } from '../../i18n/LanguageContext.jsx';
import { useAuth } from './AuthContext.jsx';
import { useGoogleIdentity } from './useGoogleIdentity.js';
import TurnstileChallenge, { isTurnstileEnabled } from '../organization/components/TurnstileChallenge.jsx';
import {
  ORGANIZATION_AUTH_INTENT,
  getPostAuthRedirectPath,
} from '../organization/organizationFlow.js';

const COOLDOWN_SECONDS = 60;
const VITE_GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const BRAND_LOGO_SRC = '/BidWise Icon.png';

/* ─────────────────────────────────────────────────────────────
   AuthLoadingState
   Shown only while useAuth() checks an existing session on
   mount. Uses an indeterminate progress bar — honest, no fake %.
───────────────────────────────────────────────────────────── */
const AuthLoadingState = () => {
  const { t } = useLanguage();

  return (
  <section
    className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-12"
    aria-label={t('auth.loadingSession')}
  >
    <style>{`
      @keyframes indeterminate {
        0%   { margin-left: -40%; width: 40%; }
        60%  { margin-left: 80%; width: 40%; }
        100% { margin-left: 100%; width: 10%; }
      }
    `}</style>

    <div className="relative w-full max-w-sm overflow-hidden rounded-lg border border-neutral-200 bg-white p-8 text-center">
      <div className="absolute top-0 left-0 right-0 h-[3px] bg-neutral-100" aria-hidden="true">
        <div className="h-full bg-blue-600" style={{ animation: 'indeterminate 1.6s ease-in-out infinite' }} />
      </div>

      <img
        src={BRAND_LOGO_SRC}
        alt="BidWise"
        className="mx-auto mb-5 h-16 w-16 object-contain"
      />

      <p className="font-semibold text-neutral-900">{t('auth.preparing')}</p>
      <p className="mt-1 text-sm text-neutral-500">{t('auth.takeMoment')}</p>
    </div>
  </section>
  );
};

/* ─────────────────────────────────────────────────────────────
   OTPLogin — Indeed pattern
   After Google success: googleLoading stays true, the button
   shows a spinner, the rest of the form is disabled, and
   navigate() fires immediately with no artificial delay.
   No overlay. No skeleton. No transition component.
───────────────────────────────────────────────────────────── */
const SecurityCheckModal = ({
  open,
  status,
  error,
  resetSignal,
  onVerify,
  onExpire,
  onStatusChange,
  onClose,
}) => {
  const { t } = useLanguage();

  if (!open) return null;

  const isSending = status === 'verified' && !error;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/50 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="security-check-title"
    >
      <div className="w-full max-w-sm rounded-lg border border-neutral-200 bg-white p-5 shadow-xl">
        <div className="mb-4">
          <h2 id="security-check-title" className="text-lg font-semibold text-neutral-950">
            {t('auth.quickVerification')}
          </h2>
        </div>

        {error ? (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <TurnstileChallenge
          onVerify={onVerify}
          onExpire={onExpire}
          onStatusChange={onStatusChange}
          resetSignal={resetSignal}
        />

        {isSending ? (
          <div className="mt-4 flex items-center justify-center gap-2 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-800">
            <Spinner size={14} className="text-blue-700" />
            {t('auth.securitySending')}
          </div>
        ) : null}

        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-md border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          {t('common.cancel')}
        </button>
      </div>
    </div>
  );
};

const OTPLogin = () => {
  const { t } = useLanguage();
  const {
    requestOTP,
    verifyOTP,
    loginWithGoogle,
    error: authError,
    isAuthenticated,
    user,
    loading,
    setError: setAuthError,
  } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const organizationIntent = searchParams.get('intent') === ORGANIZATION_AUTH_INTENT;
  const headingRef = useRef(null);

  const [googleError, setGoogleError] = useState('');
  const [googleLoading, setGoogleLoading] = useState(false);

  const handleGoogleSuccess = async (idToken) => {
    setFormError('');
    setGoogleError('');
    setGoogleLoading(true);

    const result = await loginWithGoogle(idToken);

    if (result.success) {
      // Navigate immediately — the form stays mounted and
      // visually locked until React Router unmounts this page.
      navigate(
        getPostAuthRedirectPath({
          user: result.user,
          isNewUser: result.is_new_user,
          organizationIntent,
        }),
        { replace: true },
      );
    } else {
      setGoogleLoading(false);
      setGoogleError(result.error);
    }
  };

  const handleGoogleError = (msg) => setGoogleError(msg);

  const { containerRef: googleBtnRef, ready: googleReady } = useGoogleIdentity(
    handleGoogleSuccess,
    handleGoogleError,
  );

  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [showGoogleOnly, setShowGoogleOnly] = useState(false);

  useEffect(() => {
    setShowGoogleOnly(/@gmail\.com$/i.test(email.trim()));
  }, [email]);

  const [emailError, setEmailError] = useState('');
  const [otpError, setOtpError] = useState('');
  const [formError, setFormError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [securityModalOpen, setSecurityModalOpen] = useState(false);
  const [securityStatus, setSecurityStatus] = useState(isTurnstileEnabled() ? 'loading' : 'disabled');
  const [securityError, setSecurityError] = useState('');
  const [turnstileResetKey, setTurnstileResetKey] = useState(0);
  const otpRequestInFlightRef = useRef(false);

  const clearTransientErrors = useCallback(() => {
    setEmailError('');
    setOtpError('');
    setFormError('');
    setGoogleError('');
    setSecurityError('');
    setAuthError(null);
  }, [setAuthError]);

  useEffect(() => {
    if (isAuthenticated) {
      navigate(
        getPostAuthRedirectPath({ user, organizationIntent }),
        { replace: true },
      );
    }
  }, [isAuthenticated, user, navigate, organizationIntent]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => setCooldown((p) => (p <= 1 ? 0 : p - 1)), 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  useEffect(() => {
    headingRef.current?.focus();
  }, [step]);

  const validateEmail = () => {
    if (!email.trim()) { setEmailError(t('auth.emailRequired')); return false; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError(t('auth.invalidEmail'));
      return false;
    }
    setEmailError('');
    return true;
  };

  const sendOTPRequest = async (turnstileToken = '') => {
    if (otpRequestInFlightRef.current) return;
    otpRequestInFlightRef.current = true;
    setIsLoading(true);
    setSecurityError('');
    const result = await requestOTP(email, turnstileToken);
    setIsLoading(false);
    otpRequestInFlightRef.current = false;

    if (result.success) {
      setSecurityModalOpen(false);
      setStep(2);
      setCooldown(COOLDOWN_SECONDS);
    } else {
      setTurnstileResetKey((value) => value + 1);
      if (securityModalOpen) {
        setSecurityError(result.error);
        setSecurityStatus(isTurnstileEnabled() ? 'loading' : 'disabled');
      } else {
        setFormError(result.error);
      }
    }
  };

  const handleRequestOTP = async (event) => {
    event.preventDefault();
    clearTransientErrors();
    if (!validateEmail()) return;

    if (isTurnstileEnabled()) {
      setSecurityStatus('loading');
      setSecurityModalOpen(true);
      setTurnstileResetKey((value) => value + 1);
      return;
    }

    await sendOTPRequest();
  };

  const validateOTP = () => {
    if (!otp.trim()) { setOtpError(t('auth.codeRequired')); return false; }
    if (!/^\d{6}$/.test(otp.trim())) {
      setOtpError(t('auth.invalidCode'));
      return false;
    }
    setOtpError('');
    return true;
  };

  const handleVerifyOTP = async (event) => {
    event.preventDefault();
    setFormError('');
    setAuthError(null);
    if (!validateOTP()) return;
    setIsLoading(true);
    const result = await verifyOTP(email, otp.trim());
    setIsLoading(false);
    if (result.success) {
      navigate(
        getPostAuthRedirectPath({
          user: result.user,
          isNewUser: result.is_new_user,
          organizationIntent,
        }),
        { replace: true },
      );
    } else {
      setFormError(result.error);
    }
  };

  const handleResend = useCallback(async () => {
    if (cooldown > 0) return;
    setFormError('');
    setOtp('');
    setOtpError('');
    setAuthError(null);
    if (isTurnstileEnabled()) {
      setSecurityError('');
      setSecurityStatus('loading');
      setSecurityModalOpen(true);
      setTurnstileResetKey((value) => value + 1);
      return;
    }
    await sendOTPRequest();
  }, [cooldown, requestOTP, setAuthError]);

  const handleBack = () => {
    setStep(1);
    setOtp('');
    setCooldown(0);
    clearTransientErrors();
  };

  if (loading) return <AuthLoadingState />;

  return (
    <section
      className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-12"
      aria-labelledby="login-heading"
    >
      <div className="absolute right-4 top-4">
        <LanguageToggle />
      </div>
      <SecurityCheckModal
        open={securityModalOpen}
        status={securityStatus}
        error={securityError}
        resetSignal={turnstileResetKey}
        onVerify={(token) => {
          setSecurityStatus('verified');
          void sendOTPRequest(token);
        }}
        onExpire={() => {
          setSecurityError('');
        }}
        onStatusChange={setSecurityStatus}
        onClose={() => {
          if (isLoading) return;
          setSecurityModalOpen(false);
          setSecurityError('');
        }}
      />
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="mb-8 text-center">
          <Link
            to={organizationIntent ? '/organizations' : '/'}
            className="mb-4 inline-flex items-center gap-2"
            aria-label={t('auth.bidwiseHome')}
          >
            <img src={BRAND_LOGO_SRC} alt="BidWise Logo" className="h-30 w-30 object-contain" />
          </Link>
          {step === 1 ? (
            <>
              <h1
                id="login-heading"
                ref={headingRef}
                tabIndex={-1}
                className="mb-2 text-2xl font-bold text-neutral-900 outline-none"
              >
                {t('auth.signInToBidWise')}
              </h1>
              <p className="text-neutral-600">
                {organizationIntent
                  ? ''
                  : ''}
              </p>
            </>
          ) : (
            <>
              <h1
                id="login-heading"
                ref={headingRef}
                tabIndex={-1}
                className="mb-2 text-2xl font-bold text-neutral-900 outline-none"
              >
                {t('auth.enterCode')}
              </h1>
              <p className="text-neutral-600">
                {t('auth.weSentCode')}{' '}
                <span className="font-medium text-neutral-900">{email}</span>
              </p>
            </>
          )}
        </div>

        {/* Card */}
        <div className="rounded-lg border border-neutral-200 bg-white p-8">

          {/* ── Step 1: Email ── */}
          {step === 1 && (
            showGoogleOnly ? (
              <div className="space-y-6" aria-label={t('auth.signInGoogle')}>
                <div className="mb-2 text-center">
                  <h2 className="text-xl font-semibold text-neutral-900 mb-1">
                    {t('auth.googleWelcome')}
                  </h2>
                  <p className="text-neutral-700 mb-1">
                    {t('auth.googleManaged')}
                  </p>
                  <p className="text-neutral-700 mb-1">
                    {t('auth.continueAs')} <span className="font-bold">{email}</span>.
                  </p>
                  <button
                    type="button"
                    className="text-sm text-blue-600 hover:underline mb-2"
                    onClick={() => setEmail('')}
                  >
                    {t('auth.switchAccount')}
                  </button>
                </div>

                {(formError || authError || googleError) && (
                  <div role="alert" aria-live="assertive">
                    <Alert variant="destructive">
                      <AlertDescription>{formError || authError || googleError}</AlertDescription>
                    </Alert>
                  </div>
                )}

                {VITE_GOOGLE_CLIENT_ID && (
                  <div className="relative mb-4">
                    {googleReady ? (
                      <div
                        ref={googleBtnRef}
                        className={googleLoading ? 'pointer-events-none opacity-50' : ''}
                      />
                    ) : (
                      <div className="flex h-[44px] w-full items-center justify-center rounded border border-neutral-200 bg-white">
                        <span className="text-sm text-neutral-400">{t('auth.loading')}</span>
                      </div>
                    )}
                    {googleLoading && (
                      <div
                        className="mt-2 flex items-center justify-center gap-1.5 text-sm text-neutral-500"
                        aria-live="polite"
                      >
                        <Spinner size={13} className="text-blue-500" />
                        {t('auth.signingIn')}
                      </div>
                    )}
                  </div>
                )}

                <div className="text-xs text-neutral-500 text-left mb-2">
                  {t('auth.googlePolicy')}
                </div>

                <div className="text-center">
                  <button
                    type="button"
                    className="text-sm text-blue-600 hover:underline"
                    onClick={() => setShowGoogleOnly(false)}
                  >
                    {t('auth.signInCode')}
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleRequestOTP} className="space-y-6" aria-label={t('auth.signInWithEmail')}>
                {(formError || authError || googleError) && (
                  <div role="alert" aria-live="assertive">
                    <Alert variant="destructive">
                      <AlertDescription>{formError || authError || googleError}</AlertDescription>
                    </Alert>
                  </div>
                )}

                {VITE_GOOGLE_CLIENT_ID && (
                  <>
                    <div className="relative">
                      {googleReady ? (
                        <div
                          ref={googleBtnRef}
                          className={googleLoading ? 'pointer-events-none opacity-50' : ''}
                        />
                      ) : (
                        <div className="flex h-[44px] w-full items-center justify-center rounded border border-neutral-200 bg-white">
                          <span className="text-sm text-neutral-400">{t('auth.loading')}</span>
                        </div>
                      )}
                      {googleLoading && (
                        <div
                          className="mt-2 flex items-center justify-center gap-1.5 text-sm text-neutral-500"
                          aria-live="polite"
                        >
                          <Spinner size={13} className="text-blue-500" />
                          {t('auth.signingIn')}
                        </div>
                      )}
                    </div>

                    <div className="relative flex items-center">
                      <div className="flex-grow border-t border-neutral-200" />
                      <span className="mx-3 shrink-0 text-xs text-neutral-400">{t('common.or')}</span>
                      <div className="flex-grow border-t border-neutral-200" />
                    </div>
                  </>
                )}

                <div className="space-y-2">
                  <Label htmlFor="email">{t('auth.emailAddress')}</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (emailError) setEmailError('');
                      if (formError || authError || googleError) {
                        setFormError('');
                        setGoogleError('');
                        setAuthError(null);
                      }
                    }}
                    disabled={isLoading || googleLoading}
                    autoComplete="email"
                    autoFocus
                    aria-label={t('auth.emailAddress')}
                    aria-required="true"
                    aria-invalid={emailError ? 'true' : 'false'}
                    aria-describedby={emailError ? 'email-error' : undefined}
                  />
                  {emailError && (
                    <p id="email-error" className="text-sm text-red-600">{emailError}</p>
                  )}
                </div>

                <Button type="submit" className="w-full" disabled={isLoading || googleLoading}>
                  {isLoading ? (
                    <>
                      <Spinner size={16} className="mr-2" />
                      {t('auth.sendingCode')}
                    </>
                  ) : (
                    <>
                      <Mail className="mr-2 h-4 w-4" />
                      {t('auth.sendCode')}
                    </>
                  )}
                </Button>
              </form>
            )
          )}

          {/* ── Step 2: OTP ── */}
          {step === 2 && (
            <form onSubmit={handleVerifyOTP} className="space-y-6" aria-label={t('auth.verifyOtp')}>
              <div
                className="flex items-center gap-2 rounded-md bg-green-50 p-3 text-sm text-green-800"
                role="status"
              >
                <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-green-600" aria-hidden="true" />
                {t('auth.codeSent')}
              </div>

              {(formError || authError) && (
                <div role="alert" aria-live="assertive">
                  <Alert variant="destructive">
                    <AlertDescription>{formError || authError}</AlertDescription>
                  </Alert>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="otp">{t('auth.sixDigitCode')}</Label>
                <Input
                  id="otp"
                  type="text"
                  inputMode="numeric"
                  placeholder="000000"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, '');
                    setOtp(val);
                    if (otpError) setOtpError('');
                    if (formError || authError) {
                      setFormError('');
                      setAuthError(null);
                    }
                  }}
                  disabled={isLoading}
                  autoComplete="one-time-code"
                  autoFocus
                  className="text-center text-2xl tracking-[0.5em]"
                  aria-label={t('auth.sixDigitVerificationCode')}
                  aria-required="true"
                  aria-invalid={otpError ? 'true' : 'false'}
                  aria-describedby={otpError ? 'otp-error' : undefined}
                />
                {otpError && (
                  <p id="otp-error" className="text-sm text-red-600">{otpError}</p>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Spinner size={16} className="mr-2" />
                    {t('auth.verifying')}
                  </>
                ) : (
                  t('auth.verifySignIn')
                )}
              </Button>

              <div className="flex items-center justify-between text-sm">
                <button
                  type="button"
                  onClick={handleBack}
                  className="flex items-center gap-1 text-neutral-600 hover:text-neutral-900"
                >
                  <ArrowLeft className="h-3 w-3" />
                  {t('auth.changeEmail')}
                </button>
                {cooldown > 0 ? (
                  <span className="text-neutral-500">{t('auth.resendIn', { seconds: cooldown })}</span>
                ) : (
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={isLoading}
                    className="font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50"
                  >
                    {t('auth.resendCode')}
                  </button>
                )}
              </div>
            </form>
          )}
        </div>


      </div>
    </section>
  );
};

export default OTPLogin;
