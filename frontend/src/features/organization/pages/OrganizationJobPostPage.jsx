import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Loader2 } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select.jsx';
import { Textarea } from '../../../components/ui/textarea.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import AiDescriptionDraftButton from '../components/AiDescriptionDraftButton.jsx';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import { ErrorSummary, SubmitNotice } from '../components/OpportunityPostFields.jsx';
import TurnstileChallenge, { isTurnstileEnabled } from '../components/TurnstileChallenge.jsx';
import useOrganizationOpportunityEdit, {
  normalizeDateInputValue,
  normalizeOptionValue,
} from '../hooks/useOrganizationOpportunityEdit.js';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  ORGANIZATION_OPPORTUNITY_SUBMITTED_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import {
  createOrganizationOpportunity,
  parseOrganizationApiError,
  updateOrganizationOpportunity,
} from '../services/organizationService.js';
import { TUNISIAN_LOCATION_OPTIONS } from '../../profile/profilePreferences.js';

const INITIAL_VALUES = {
  title: '',
  location: '',
  description: '',
  contract: 'CDI',
  availability: 'On site',
  experience_min: '',
  experience_max: '',
  education_level: '',
  salary: '',
  skills: '',
  deadline: '',
};

const CONTRACT_TYPES = [
  { value: 'CDI', label: 'CDI' },
  { value: 'CDD', label: 'CDD' },
  { value: 'SIVP', label: 'CIVP' },
  { value: 'Freelance', label: 'Freelance' },
  { value: 'Contract', label: 'Contract' },
];
const AVAILABILITY_OPTIONS = ['On site', 'Hybrid', 'Remote', 'Full time', 'Part time'];
const FIELD_CLASS = 'h-11 rounded-xl border-neutral-300 bg-white text-sm focus-visible:ring-blue-500';

const splitSkills = (value) =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item, index, list) => list.findIndex((other) => other.toLowerCase() === item.toLowerCase()) === index);

const normalizeOptionalNumber = (value) => {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const isDigitsOnly = (value) => /^\d*$/.test(value);

const FieldError = ({ message }) => (
  message ? <p className="mt-2 text-sm text-red-600">{message}</p> : null
);

const ERROR_LABELS = {
  title: 'Job title',
  contract: 'Contract type',
  location: 'Location',
  description: 'Job description',
  skills: 'Skills',
  experience_min: 'Minimum experience',
  experience_max: 'Maximum experience',
  salary: 'Salary',
  deadline: 'Application deadline',
};

const OrganizationJobPostPage = () => {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const profile = user?.organization_profile;
  const edit = useOrganizationOpportunityEdit('EMPLOI');
  const [values, setValues] = useState(INITIAL_VALUES);
  const [errors, setErrors] = useState({});
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState('');
  const [turnstileResetKey, setTurnstileResetKey] = useState(0);
  const [turnstileStatus, setTurnstileStatus] = useState(isTurnstileEnabled() ? 'loading' : 'disabled');

  useEffect(() => {
    if (!edit.opportunity) return;
    const item = edit.opportunity;
    setValues({
      title: item.title || '',
      location: normalizeOptionValue(item.location, TUNISIAN_LOCATION_OPTIONS),
      description: item.description || '',
      contract: item.contract || 'CDI',
      availability: item.availability || 'On site',
      experience_min: item.experience_min ?? '',
      experience_max: item.experience_max ?? '',
      education_level: item.education_level || '',
      salary: item.salary || '',
      skills: Array.isArray(item.skills) ? item.skills.join(', ') : '',
      deadline: normalizeDateInputValue(item.deadline),
    });
  }, [edit.opportunity]);

  const skillsPreview = useMemo(() => splitSkills(values.skills), [values.skills]);

  const updateValue = (name, value) => {
    setValues((previous) => ({ ...previous, [name]: value }));
    setErrors((previous) => ({ ...previous, [name]: '' }));
    setSubmitError('');
  };

  const updateExperienceValue = (name, value) => {
    if (!isDigitsOnly(value)) {
      setErrors((previous) => ({
        ...previous,
        [name]: 'Use digits only. Negative values are not allowed.',
      }));
      return;
    }
    updateValue(name, value);
  };

  const updateSalaryValue = (value) => {
    if (/(^|[\s:])-\s*\d/.test(value)) {
      setErrors((previous) => ({
        ...previous,
        salary: 'Salary cannot be negative.',
      }));
      return;
    }
    updateValue('salary', value);
  };

  const validate = () => {
    const nextErrors = {};
    const minYears = normalizeOptionalNumber(values.experience_min);
    const maxYears = normalizeOptionalNumber(values.experience_max);
    const salary = values.salary.trim();

    if (values.title.trim().length < 5) {
      nextErrors.title = 'Enter a clear job title with at least 5 characters.';
    }
    if (!TUNISIAN_LOCATION_OPTIONS.includes(values.location)) {
      nextErrors.location = 'Choose a valid Tunisian location.';
    }
    if (values.description.trim().length < 40) {
      nextErrors.description = 'Add at least 40 characters describing the job.';
    }
    if (values.experience_min !== '' && (minYears === null || minYears < 0 || minYears > 60)) {
      nextErrors.experience_min = 'Use a value between 0 and 60.';
    }
    if (values.experience_max !== '' && (maxYears === null || maxYears < 0 || maxYears > 60)) {
      nextErrors.experience_max = 'Use a value between 0 and 60.';
    }
    if (minYears !== null && maxYears !== null && minYears > maxYears) {
      nextErrors.experience_max = 'Maximum experience must be greater than or equal to minimum experience.';
    }
    if (salary && /(^|[\s:])-\s*\d/.test(salary)) {
      nextErrors.salary = 'Salary cannot be negative.';
    }
    if (skillsPreview.length > 15) {
      nextErrors.skills = 'Use up to 15 skills.';
    }
    return nextErrors;
  };

  const buildPayload = () => ({
    title: values.title.trim(),
    type: 'EMPLOI',
    location: values.location.trim(),
    description: values.description.trim(),
    contract: values.contract,
    availability: values.availability,
    experience_min: normalizeOptionalNumber(values.experience_min),
    experience_max: normalizeOptionalNumber(values.experience_max),
    education_level: values.education_level.trim(),
    salary: values.salary.trim(),
    skills: skillsPreview.slice(0, 15),
    deadline: values.deadline || null,
  });

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSubmitting) return;
    setHasAttemptedSubmit(true);

    const nextErrors = validate();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    if (isTurnstileEnabled() && !turnstileToken) {
      setSubmitError('Complete the anti-bot check before publishing.');
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitError('');
      const payload = {
        ...buildPayload(),
        turnstile_token: turnstileToken,
      };
      if (edit.isEditing) {
        await updateOrganizationOpportunity(edit.opportunityId, payload);
        navigate('/organization/dashboard', { replace: true });
      } else {
        await createOrganizationOpportunity(payload);
        navigate(ORGANIZATION_OPPORTUNITY_SUBMITTED_PATH, { replace: true });
      }
    } catch (error) {
      const parsed = parseOrganizationApiError(error);
      setErrors(parsed.fields || {});
      setSubmitError(parsed.message || 'Unable to publish this job.');
      setTurnstileToken('');
      setTurnstileResetKey((value) => value + 1);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-neutral-50 px-4">
        <div className="rounded-lg border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-600">
          Loading organization workspace
        </div>
      </section>
    );
  }

  if (edit.isLoading) {
    return <section className="flex min-h-[70vh] items-center justify-center text-sm text-neutral-600">Loading opportunity...</section>;
  }

  if (edit.loadError) {
    return <section className="flex min-h-[70vh] items-center justify-center px-4 text-center text-sm text-red-700">{edit.loadError}</section>;
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-white" aria-labelledby="publish-job-heading">
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[286px_1fr]">
        <OrganizationSidebar activePath="/organization/post" />

        <div className="min-w-0">
          <form onSubmit={handleSubmit} noValidate className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl flex-col px-5 py-10">
            <div className="flex-1">
              <div className="text-center">
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">{edit.isEditing ? 'Edit job' : 'Create a job'}</p>
                <h1 id="publish-job-heading" className="mt-3 text-4xl font-semibold tracking-tight text-neutral-950">
                  Basic information
                </h1>
                <p className="mt-4 text-sm text-neutral-600">
                  {edit.isEditing ? 'Your changes will be checked again before publication.' : 'This job will be published on BidWise and visible to qualified candidates.'}
                </p>
              </div>

              <div className="mt-14 space-y-10">
                <section className="border-t border-neutral-200 pt-8">
                  <label htmlFor="title" className="text-sm font-semibold text-neutral-900">Job title *</label>
                  <Input id="title" value={values.title} onChange={(event) => updateValue('title', event.target.value)} className={`mt-2 ${FIELD_CLASS}`} aria-invalid={errors.title ? 'true' : 'false'} />
                  <FieldError message={errors.title} />
                </section>

                <section className="border-t border-neutral-200 pt-8">
                  <div className="grid gap-5 md:grid-cols-2">
                    <div>
                      <label htmlFor="contract" className="text-sm font-semibold text-neutral-900">Contract *</label>
                      <Select value={values.contract} onValueChange={(value) => updateValue('contract', value)}>
                        <SelectTrigger id="contract" className={`mt-2 ${FIELD_CLASS}`}>
                          <SelectValue placeholder="Select contract" />
                        </SelectTrigger>
                        <SelectContent>
                          {CONTRACT_TYPES.map((item) => (
                            <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FieldError message={errors.contract} />
                    </div>
                    <div>
                      <label htmlFor="availability" className="text-sm font-semibold text-neutral-900">Work mode *</label>
                      <Select value={values.availability} onValueChange={(value) => updateValue('availability', value)}>
                        <SelectTrigger id="availability" className={`mt-2 ${FIELD_CLASS}`}>
                          <SelectValue placeholder="Select work mode" />
                        </SelectTrigger>
                        <SelectContent>
                          {AVAILABILITY_OPTIONS.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </section>

                <section className="border-t border-neutral-200 pt-8">
                  <label htmlFor="location" className="text-sm font-semibold text-neutral-900">Where is this job located? *</label>
                  <p className="mt-1 text-sm text-neutral-500">Choose a Tunisian city or region from the approved list.</p>
                  <Select value={values.location} onValueChange={(value) => updateValue('location', value)}>
                    <SelectTrigger id="location" className={`mt-2 ${FIELD_CLASS}`} aria-invalid={errors.location ? 'true' : 'false'}>
                      <SelectValue placeholder="Select location" />
                    </SelectTrigger>
                    <SelectContent>
                      {TUNISIAN_LOCATION_OPTIONS.map((item) => (
                        <SelectItem key={item} value={item}>{item}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FieldError message={errors.location} />
                </section>

                <section className="border-t border-neutral-200 pt-8">
                  <label htmlFor="skills" className="text-sm font-semibold text-neutral-900">Skills</label>
                  <p className="mt-1 text-sm text-neutral-500">Separate skills with commas. Example: Java, SQL, Docker.</p>
                  <Input id="skills" value={values.skills} onChange={(event) => updateValue('skills', event.target.value)} className={`mt-2 ${FIELD_CLASS}`} aria-invalid={errors.skills ? 'true' : 'false'} />
                  {skillsPreview.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {skillsPreview.slice(0, 15).map((skill) => (
                        <span key={skill} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">{skill}</span>
                      ))}
                    </div>
                  ) : null}
                  <FieldError message={errors.skills} />
                </section>

                <section className="border-t border-neutral-200 pt-8">
                  <div className="grid gap-5 md:grid-cols-2">
                    <div>
                      <label htmlFor="experience_min" className="text-sm font-semibold text-neutral-900">Minimum experience</label>
                      <Input
                        id="experience_min"
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        value={values.experience_min}
                        onChange={(event) => updateExperienceValue('experience_min', event.target.value)}
                        className={`mt-2 ${FIELD_CLASS}`}
                        aria-invalid={errors.experience_min ? 'true' : 'false'}
                      />
                      <FieldError message={errors.experience_min} />
                    </div>
                    <div>
                      <label htmlFor="experience_max" className="text-sm font-semibold text-neutral-900">Maximum experience</label>
                      <Input
                        id="experience_max"
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        value={values.experience_max}
                        onChange={(event) => updateExperienceValue('experience_max', event.target.value)}
                        className={`mt-2 ${FIELD_CLASS}`}
                        aria-invalid={errors.experience_max ? 'true' : 'false'}
                      />
                      <FieldError message={errors.experience_max} />
                    </div>
                  </div>
                </section>

                <section className="border-t border-neutral-200 pt-8">
                  <div className="grid gap-5 md:grid-cols-3">
                    <div>
                      <label htmlFor="education_level" className="text-sm font-semibold text-neutral-900">Education level</label>
                      <Input id="education_level" value={values.education_level} onChange={(event) => updateValue('education_level', event.target.value)} className={`mt-2 ${FIELD_CLASS}`} placeholder="Example: Bac+3" />
                    </div>
                    <div>
                      <label htmlFor="salary" className="text-sm font-semibold text-neutral-900">Salary</label>
                      <Input id="salary" value={values.salary} onChange={(event) => updateSalaryValue(event.target.value)} className={`mt-2 ${FIELD_CLASS}`} aria-invalid={errors.salary ? 'true' : 'false'} placeholder="Example: 1500 DT" />
                      <FieldError message={errors.salary} />
                    </div>
                    <div>
                      <label htmlFor="deadline" className="text-sm font-semibold text-neutral-900">Deadline</label>
                      <Input id="deadline" type="date" value={values.deadline} onChange={(event) => updateValue('deadline', event.target.value)} className={`mt-2 ${FIELD_CLASS}`} aria-invalid={errors.deadline ? 'true' : 'false'} />
                      <FieldError message={errors.deadline} />
                    </div>
                  </div>
                </section>

                <section className="border-t border-neutral-200 pt-8">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <label htmlFor="description" className="text-sm font-semibold text-neutral-900">Description *</label>
                    <AiDescriptionDraftButton
                      type="EMPLOI"
                      title={values.title}
                      contract={values.contract}
                      workMode={values.availability}
                      location={values.location}
                      skills={skillsPreview}
                      minExperience={normalizeOptionalNumber(values.experience_min)}
                      maxExperience={normalizeOptionalNumber(values.experience_max)}
                      educationLevel={values.education_level}
                      salary={values.salary}
                      deadline={values.deadline}
                      currentDescription={values.description}
                      onApply={(description) => updateValue('description', description)}
                    />
                  </div>
                  <p className="mt-1 text-sm text-neutral-500">Include mission, responsibilities, requirements, and benefits.</p>
                  <Textarea id="description" value={values.description} onChange={(event) => updateValue('description', event.target.value)} className="mt-2 min-h-40 rounded-xl border-neutral-300 bg-white text-sm focus-visible:ring-blue-500" aria-invalid={errors.description ? 'true' : 'false'} />
                  <FieldError message={errors.description} />
                </section>

                <SubmitNotice
                  message={submitError}
                  tone={submitError.startsWith('Publishing limit reached') ? 'warning' : 'error'}
                />
                <TurnstileChallenge
                  onVerify={setTurnstileToken}
                  onExpire={() => setTurnstileToken('')}
                  onStatusChange={setTurnstileStatus}
                  resetSignal={turnstileResetKey}
                />
                {hasAttemptedSubmit ? <ErrorSummary errors={errors} labels={ERROR_LABELS} /> : null}
              </div>
            </div>

            <div className="sticky bottom-0 mt-10 flex items-center justify-between border-t border-neutral-200 bg-white py-4">
              <Button type="button" variant="outline" asChild className="h-11 rounded-xl">
                <Link to="/organization/post">Back</Link>
              </Button>
              <Button type="submit" className="h-11 rounded-xl bg-blue-700 px-5 text-white hover:bg-blue-800" disabled={isSubmitting || (isTurnstileEnabled() && turnstileStatus !== 'verified')}>
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
                {isSubmitting ? (edit.isEditing ? 'Saving changes...' : 'Publishing...') : edit.isEditing ? 'Save changes' : 'Publish job'}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
};

export default OrganizationJobPostPage;
