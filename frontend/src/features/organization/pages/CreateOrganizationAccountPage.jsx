import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Building2, CheckCircle2, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../../../components/ui/alert.jsx';
import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import { Spinner } from '../../../components/ui/spinner.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_DASHBOARD_PATH,
  ORGANIZATION_TYPES,
  buildOrganizationProfilePayload,
  isOrganizationAccount,
  isOrganizationProfileComplete,
  validateOrganizationProfileForm,
} from '../organizationFlow.js';
import {
  parseOrganizationApiError,
  upsertOrganizationProfile,
} from '../services/organizationService.js';

const initialValues = {
  organization_name: '',
  first_name: '',
  last_name: '',
  website: '',
  phone: '+216 ',
  organization_type: '',
  how_did_you_hear_about_us: '',
};

const FieldError = ({ id, message }) => {
  if (!message) return null;
  return (
    <p id={id} className="mt-1.5 text-sm text-red-600">
      {message}
    </p>
  );
};

const CreateOrganizationAccountPage = () => {
  const navigate = useNavigate();
  const headingRef = useRef(null);
  const { user, loading, refreshUser } = useAuth();
  const existingProfile = user?.organization_profile;
  const profileComplete = isOrganizationProfileComplete(existingProfile);

  const prefilledValues = useMemo(() => ({
    organization_name: existingProfile?.organization_name || '',
    first_name: existingProfile?.first_name || user?.first_name || '',
    last_name: existingProfile?.last_name || user?.last_name || '',
    website: existingProfile?.website || '',
    phone: existingProfile?.phone || '+216 ',
    organization_type: existingProfile?.organization_type || '',
    how_did_you_hear_about_us: '',
  }), [existingProfile, user]);

  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  useEffect(() => {
    if (!loading) {
      setValues(prefilledValues);
      headingRef.current?.focus();
    }
  }, [loading, prefilledValues]);

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-neutral-50 px-4">
        <div className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-600">
          <Spinner size={16} className="text-emerald-700" />
          Preparing organization setup
        </div>
      </section>
    );
  }

  if (isOrganizationAccount(user) && profileComplete && !isSubmitted) {
    return <Navigate to={ORGANIZATION_DASHBOARD_PATH} replace />;
  }

  const updateValue = (field, value) => {
    setValues((current) => ({ ...current, [field]: value }));
    if (errors[field]) {
      setErrors((current) => ({ ...current, [field]: '' }));
    }
    if (submitError) setSubmitError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextErrors = validateOrganizationProfileForm(values);
    setErrors(nextErrors);
    setSubmitError('');

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      await upsertOrganizationProfile(buildOrganizationProfilePayload(values));
      await refreshUser();
      setIsSubmitted(true);
      navigate(ORGANIZATION_DASHBOARD_PATH, { replace: true });
    } catch (error) {
      const parsedError = parseOrganizationApiError(error);
      setErrors(parsedError.fields || {});
      setSubmitError(parsedError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="min-h-screen bg-neutral-50" aria-labelledby="organization-create-heading">
      <div className="mx-auto grid min-h-screen max-w-7xl gap-0 px-4 py-8 sm:px-6 lg:grid-cols-[0.78fr_1.22fr] lg:px-8">
        <aside className="flex flex-col justify-between rounded-t-lg border border-neutral-200 bg-neutral-950 p-6 text-white lg:rounded-l-lg lg:rounded-tr-none lg:p-8">
          <div>
            <Link to="/organizations" className="inline-flex items-center gap-2 text-sm font-medium text-neutral-200 hover:text-white">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to organizations
            </Link>
            <div className="mt-10">
              <div className="flex h-12 w-12 items-center justify-center rounded-md bg-white text-neutral-950">
                <Building2 className="h-6 w-6" aria-hidden="true" />
              </div>
              <h1
                id="organization-create-heading"
                ref={headingRef}
                tabIndex={-1}
                className="mt-6 text-3xl font-semibold leading-tight text-white outline-none"
              >
                Create your organization account.
              </h1>
              <p className="mt-4 text-sm leading-6 text-neutral-300">
                Tell us who is publishing opportunities. These details keep promoter accounts clear, trustworthy, and ready for future posting tools.
              </p>
            </div>
          </div>

          <div className="mt-10 space-y-4 text-sm text-neutral-300">
            {[
              'One shared BidWise sign-in',
              'Tunisia phone verification format',
              'Clean organization profile foundation',
            ].map((item) => (
              <div key={item} className="flex items-center gap-3">
                <CheckCircle2 className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </aside>

        <div className="rounded-b-lg border-x border-b border-neutral-200 bg-white p-6 shadow-sm lg:rounded-r-lg lg:rounded-bl-none lg:border-y lg:border-r lg:border-l-0 lg:p-10">
          <div className="mb-8 max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Organization setup</p>
            <h2 className="mt-3 text-2xl font-semibold text-neutral-950">Profile details</h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              Required fields are marked with an asterisk.
            </p>
          </div>

          {submitError ? (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="mr-2 inline h-4 w-4" aria-hidden="true" />
              <AlertDescription>{submitError}</AlertDescription>
            </Alert>
          ) : null}

          <form onSubmit={handleSubmit} className="max-w-3xl space-y-6" noValidate>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Label htmlFor="organization_name">Organization name *</Label>
                <Input
                  id="organization_name"
                  value={values.organization_name}
                  onChange={(event) => updateValue('organization_name', event.target.value)}
                  placeholder="Acme Tunisia"
                  autoComplete="organization"
                  aria-required="true"
                  aria-invalid={errors.organization_name ? 'true' : 'false'}
                  aria-describedby={errors.organization_name ? 'organization_name-error' : undefined}
                  className="mt-2 h-11 bg-white"
                />
                <FieldError id="organization_name-error" message={errors.organization_name} />
              </div>

              <div>
                <Label htmlFor="first_name">First name *</Label>
                <Input
                  id="first_name"
                  value={values.first_name}
                  onChange={(event) => updateValue('first_name', event.target.value)}
                  placeholder="Lina"
                  autoComplete="given-name"
                  aria-required="true"
                  aria-invalid={errors.first_name ? 'true' : 'false'}
                  aria-describedby={errors.first_name ? 'first_name-error' : undefined}
                  className="mt-2 h-11 bg-white"
                />
                <FieldError id="first_name-error" message={errors.first_name} />
              </div>

              <div>
                <Label htmlFor="last_name">Last name *</Label>
                <Input
                  id="last_name"
                  value={values.last_name}
                  onChange={(event) => updateValue('last_name', event.target.value)}
                  placeholder="Mansour"
                  autoComplete="family-name"
                  aria-required="true"
                  aria-invalid={errors.last_name ? 'true' : 'false'}
                  aria-describedby={errors.last_name ? 'last_name-error' : undefined}
                  className="mt-2 h-11 bg-white"
                />
                <FieldError id="last_name-error" message={errors.last_name} />
              </div>

              <div>
                <Label htmlFor="website">Website</Label>
                <Input
                  id="website"
                  value={values.website}
                  onChange={(event) => updateValue('website', event.target.value)}
                  placeholder="https://example.com"
                  autoComplete="url"
                  aria-invalid={errors.website ? 'true' : 'false'}
                  aria-describedby={errors.website ? 'website-error' : undefined}
                  className="mt-2 h-11 bg-white"
                />
                <FieldError id="website-error" message={errors.website} />
              </div>

              <div>
                <Label htmlFor="phone">Phone *</Label>
                <Input
                  id="phone"
                  value={values.phone}
                  onChange={(event) => updateValue('phone', event.target.value)}
                  placeholder="+216 12345678"
                  autoComplete="tel"
                  aria-required="true"
                  aria-invalid={errors.phone ? 'true' : 'false'}
                  aria-describedby={errors.phone ? 'phone-error' : undefined}
                  className="mt-2 h-11 bg-white"
                />
                <FieldError id="phone-error" message={errors.phone} />
              </div>

              <div>
                <Label htmlFor="organization_type">Organization type *</Label>
                <select
                  id="organization_type"
                  value={values.organization_type}
                  onChange={(event) => updateValue('organization_type', event.target.value)}
                  aria-required="true"
                  aria-invalid={errors.organization_type ? 'true' : 'false'}
                  aria-describedby={errors.organization_type ? 'organization_type-error' : undefined}
                  className="mt-2 h-11 w-full rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900 focus-visible:border-blue-500 focus-visible:ring-[3px] focus-visible:ring-blue-500/30"
                >
                  <option value="">Select type</option>
                  {ORGANIZATION_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                <FieldError id="organization_type-error" message={errors.organization_type} />
              </div>

              <div>
                <Label htmlFor="how_did_you_hear_about_us">How did you hear about us?</Label>
                <Input
                  id="how_did_you_hear_about_us"
                  value={values.how_did_you_hear_about_us}
                  onChange={(event) => updateValue('how_did_you_hear_about_us', event.target.value)}
                  placeholder="LinkedIn, referral, event..."
                  className="mt-2 h-11 bg-white"
                />
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-neutral-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-neutral-500">
                You can update these details later from your organization workspace.
              </p>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="h-11 rounded-md bg-neutral-950 px-6 text-white hover:bg-neutral-800"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Saving
                  </>
                ) : (
                  'Continue'
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
};

export default CreateOrganizationAccountPage;
