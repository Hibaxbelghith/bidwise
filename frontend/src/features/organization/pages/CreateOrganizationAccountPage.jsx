import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Building2, CheckCircle2, Loader2, Upload } from 'lucide-react';
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
  validateOrganizationProfileForm,
} from '../organizationFlow.js';
import {
  parseOrganizationApiError,
  uploadOrganizationLogo,
  upsertOrganizationProfile,
} from '../services/organizationService.js';
import { useLanguage } from '../../../i18n/LanguageContext.jsx';

const initialValues = {
  organization_name: '',
  first_name: '',
  last_name: '',
  website: '',
  logo: '',
  phone: '+216 ',
  organization_type: '',
  how_did_you_hear_about_us: '',
};

const API_BASE_URL = String(import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

const resolveLogoPreviewSrc = (value) => {
  const logo = String(value || '').trim();
  if (!logo) return '';
  if (logo.startsWith('/media/')) {
    try {
      return `${new URL(API_BASE_URL, window.location.origin).origin}${logo}`;
    } catch {
      return logo;
    }
  }
  return logo;
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
  const { t } = useLanguage();
  const navigate = useNavigate();
  const headingRef = useRef(null);
  const logoFileInputRef = useRef(null);
  const { user, loading, refreshUser } = useAuth();
  const existingProfile = user?.organization_profile;
  const isEditingProfile = Boolean(existingProfile);

  const prefilledValues = useMemo(() => ({
    organization_name: existingProfile?.organization_name || '',
    first_name: existingProfile?.first_name || user?.first_name || '',
    last_name: existingProfile?.last_name || user?.last_name || '',
    website: existingProfile?.website || '',
    logo: existingProfile?.logo || '',
    phone: existingProfile?.phone || '+216 ',
    organization_type: existingProfile?.organization_type || '',
    how_did_you_hear_about_us: '',
  }), [existingProfile, user]);

  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isUploadingLogo, setIsUploadingLogo] = useState(false);
  const [logoUploadError, setLogoUploadError] = useState('');

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
          {t('organization.preparingSetup')}
        </div>
      </section>
    );
  }

  const updateValue = (field, value) => {
    setValues((current) => ({ ...current, [field]: value }));
    if (errors[field]) {
      setErrors((current) => ({ ...current, [field]: '' }));
    }
    if (submitError) setSubmitError('');
    if (submitSuccess) setSubmitSuccess('');
    if (field === 'logo' && logoUploadError) setLogoUploadError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextErrors = validateOrganizationProfileForm(values, t);
    setErrors(nextErrors);
    setSubmitError('');
    setSubmitSuccess('');

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      await upsertOrganizationProfile(buildOrganizationProfilePayload(values));
      await refreshUser();
      if (isEditingProfile) {
        setSubmitSuccess(t('organization.profileUpdated'));
      } else {
        setIsSubmitted(true);
        navigate(ORGANIZATION_DASHBOARD_PATH, { replace: true });
      }
    } catch (error) {
      const parsedError = parseOrganizationApiError(error);
      setErrors(parsedError.fields || {});
      setSubmitError(parsedError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogoUploadClick = () => {
    if (isUploadingLogo) return;
    logoFileInputRef.current?.click();
  };

  const handleLogoFileChange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setLogoUploadError('');
    setIsUploadingLogo(true);
    try {
      const uploaded = await uploadOrganizationLogo(file);
      updateValue('logo', uploaded.url || '');
    } catch (error) {
      const parsed = parseOrganizationApiError(error);
      setLogoUploadError(parsed.message || t('organization.unableUploadLogo'));
    } finally {
      setIsUploadingLogo(false);
    }
  };

  const trimmedLogo = String(values.logo || '').trim();
  const logoPreviewSrc = resolveLogoPreviewSrc(trimmedLogo);
  const showLogoPreview = Boolean(trimmedLogo) && !errors.logo;

  return (
    <section className="min-h-screen bg-neutral-50" aria-labelledby="organization-create-heading">
      <div className="mx-auto grid min-h-screen max-w-7xl gap-0 px-4 py-8 sm:px-6 lg:grid-cols-[0.78fr_1.22fr] lg:px-8">
        <aside className="flex flex-col justify-between rounded-t-lg border border-neutral-200 bg-neutral-950 p-6 text-white lg:rounded-l-lg lg:rounded-tr-none lg:p-8">
          <div>
            <Link to="/organization/dashboard" className="inline-flex items-center gap-2 text-sm font-medium text-neutral-200 hover:text-white">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              {t('common.back')}
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
                {isEditingProfile ? t('organization.updateSettingsTitle') : t('organization.createAccountTitle')}
              </h1>
              <p className="mt-4 text-sm leading-6 text-neutral-300">
                {isEditingProfile
                  ? t('organization.updateSettingsDesc')
                  : t('organization.createAccountDesc')}
              </p>
            </div>
          </div>

          <div className="mt-10 space-y-4 text-sm text-neutral-300">
            {[
              t('organization.benefitSharedSignin'),
              t('organization.benefitTunisiaPhone'),
              t('organization.benefitCleanProfile'),
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
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">
              {isEditingProfile ? t('layout.accountSettings') : t('organization.setup')}
            </p>
            <h2 className="mt-3 text-2xl font-semibold text-neutral-950">
              {isEditingProfile ? t('organization.profile') : t('organization.profileDetails')}
            </h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              {isEditingProfile
                ? t('organization.profileEditHelp')
                : t('organization.requiredFieldsHelp')}
            </p>
          </div>

          {submitError ? (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="mr-2 inline h-4 w-4" aria-hidden="true" />
              <AlertDescription>{submitError}</AlertDescription>
            </Alert>
          ) : null}
          {submitSuccess ? (
            <Alert className="mb-6 border-emerald-200 bg-emerald-50 text-emerald-900">
              <CheckCircle2 className="mr-2 inline h-4 w-4" aria-hidden="true" />
              <AlertDescription>{submitSuccess}</AlertDescription>
            </Alert>
          ) : null}

          <form onSubmit={handleSubmit} className="max-w-3xl space-y-6" noValidate>
            <div className="grid gap-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Label htmlFor="organization_name">{t('organization.organizationName')} *</Label>
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
                <Label htmlFor="first_name">{t('profile.firstName')} *</Label>
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
                <Label htmlFor="last_name">{t('profile.lastName')} *</Label>
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
                <Label htmlFor="website">{t('organization.website')}</Label>
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

              <div className="sm:col-span-2">
                <Label htmlFor="logo">{t('organization.logoUrl')}</Label>
                <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-start">
                  <div className="min-w-0 flex-1">
                    <Input
                      id="logo"
                      value={values.logo}
                      onChange={(event) => updateValue('logo', event.target.value)}
                      placeholder="https://cdn.example.com/logo.png"
                      autoComplete="url"
                      aria-invalid={errors.logo ? 'true' : 'false'}
                      aria-describedby={errors.logo ? 'logo-error' : 'logo-help'}
                      className="h-11 bg-white"
                    />
                  </div>
                  <input
                    ref={logoFileInputRef}
                    type="file"
                    accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                    className="hidden"
                    onChange={handleLogoFileChange}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleLogoUploadClick}
                    disabled={isUploadingLogo}
                    className="h-11 shrink-0 gap-2"
                  >
                    {isUploadingLogo ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        {t('organization.uploading')}
                      </>
                    ) : (
                      <>
                        <Upload className="h-4 w-4" aria-hidden="true" />
                        {t('organization.uploadImage')}
                      </>
                    )}
                  </Button>
                </div>
                <FieldError id="logo-error" message={errors.logo} />
                {logoUploadError ? (
                  <p className="mt-1.5 text-sm text-red-600">{logoUploadError}</p>
                ) : null}

                <div className="mt-4 flex items-center gap-4 rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-neutral-200 bg-white">
                    {showLogoPreview ? (
                      <img
                        src={logoPreviewSrc}
                        alt={t('organization.logoPreview')}
                        className="h-full w-full object-contain"
                        loading="lazy"
                        onError={(event) => {
                          event.currentTarget.style.display = 'none';
                          const fallback = event.currentTarget.nextElementSibling;
                          if (fallback) {
                            fallback.classList.remove('hidden');
                          }
                        }}
                        onLoad={(event) => {
                          event.currentTarget.style.display = 'block';
                          const fallback = event.currentTarget.nextElementSibling;
                          if (fallback) {
                            fallback.classList.add('hidden');
                          }
                        }}
                      />
                    ) : null}
                    <div className={`${showLogoPreview ? 'hidden' : ''} flex h-full w-full items-center justify-center`}>
                      <Building2 className="h-5 w-5 text-neutral-400" aria-hidden="true" />
                    </div>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-neutral-900">{t('organization.logoPreview')}</p>
                    <p className="text-sm text-neutral-500">
                      {showLogoPreview
                        ? t('organization.logoPreviewReady')
                        : t('organization.logoPreviewHelp')}
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <Label htmlFor="phone">{t('organization.phone')} *</Label>
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
                <Label htmlFor="organization_type">{t('organization.organizationType')} *</Label>
                <select
                  id="organization_type"
                  value={values.organization_type}
                  onChange={(event) => updateValue('organization_type', event.target.value)}
                  aria-required="true"
                  aria-invalid={errors.organization_type ? 'true' : 'false'}
                  aria-describedby={errors.organization_type ? 'organization_type-error' : undefined}
                  className="mt-2 h-11 w-full rounded-md border border-neutral-200 bg-white px-3 text-sm text-neutral-900 focus-visible:border-blue-500 focus-visible:ring-[3px] focus-visible:ring-blue-500/30"
                >
                  <option value="">{t('organization.selectType')}</option>
                  {ORGANIZATION_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {t(type.labelKey)}
                    </option>
                  ))}
                </select>
                <FieldError id="organization_type-error" message={errors.organization_type} />
              </div>

              <div>
                <Label htmlFor="how_did_you_hear_about_us">{t('organization.hearAboutUs')}</Label>
                <Input
                  id="how_did_you_hear_about_us"
                  value={values.how_did_you_hear_about_us}
                  onChange={(event) => updateValue('how_did_you_hear_about_us', event.target.value)}
                  placeholder={t('organization.hearAboutUsPlaceholder')}
                  className="mt-2 h-11 bg-white"
                />
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-neutral-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-neutral-500">
                {isEditingProfile
                  ? t('organization.editingProfileNote')
                  : t('organization.createProfileNote')}
              </p>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="h-11 rounded-md bg-neutral-950 px-6 text-white hover:bg-neutral-800"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    {t('admin.saving')}
                  </>
                ) : (
                  isEditingProfile ? t('profile.saveChanges') : t('organization.continue')
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
