import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Loader2 } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select.jsx';
import { Textarea } from '../../../components/ui/textarea.jsx';
import { TUNISIAN_LOCATION_OPTIONS } from '../../profile/profilePreferences.js';
import AiDescriptionDraftButton from '../components/AiDescriptionDraftButton.jsx';
import OpportunityPostLayout from '../components/OpportunityPostLayout.jsx';
import { ErrorSummary, FieldBlock, FieldError, SubmitNotice, fieldClassName } from '../components/OpportunityPostFields.jsx';
import TurnstileChallenge, { isTurnstileEnabled } from '../components/TurnstileChallenge.jsx';
import useOrganizationOpportunityEdit, {
  normalizeDateInputValue,
  normalizeInternshipType,
  normalizeOptionValue,
} from '../hooks/useOrganizationOpportunityEdit.js';
import {
  INTERNSHIP_DURATION_OPTIONS,
  INTERNSHIP_EDUCATION_OPTIONS,
  INTERNSHIP_TYPE_OPTIONS,
  WORK_MODE_OPTIONS,
} from '../opportunityPostConstants.js';
import { splitSkills, validateInternshipPostForm } from '../opportunityPostValidation.js';
import { ORGANIZATION_OPPORTUNITY_SUBMITTED_PATH } from '../organizationFlow.js';
import {
  createOrganizationOpportunity,
  parseOrganizationApiError,
  updateOrganizationOpportunity,
} from '../services/organizationService.js';

const INITIAL_VALUES = {
  title: '',
  location: '',
  availability: 'On site',
  internship_type: 'GRADUATION_PROJECT',
  duration: '4_6_MONTHS',
  start_date: '',
  education_level: 'Bac+5',
  description: '',
  skills: '',
  deadline: '',
};

const buildPayload = (values, skills) => ({
  type: 'STAGE',
  title: values.title.trim(),
  location: values.location,
  description: values.description.trim(),
  contract: 'Internship',
  availability: values.availability,
  education_level: values.education_level,
  skills,
  deadline: values.deadline || null,
  internship_details: {
    internship_type: values.internship_type,
    duration: values.duration,
    start_date: values.start_date,
  },
});

const ERROR_LABELS = {
  title: 'Internship title',
  location: 'Location',
  internship_type: 'Internship type',
  duration: 'Duration',
  start_date: 'Start date',
  deadline: 'Application deadline',
  description: 'Internship description',
  skills: 'Skills',
};

const OrganizationInternshipPostPage = () => {
  const navigate = useNavigate();
  const edit = useOrganizationOpportunityEdit('STAGE');
  const [values, setValues] = useState(INITIAL_VALUES);
  const [errors, setErrors] = useState({});
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState('');
  const [turnstileResetKey, setTurnstileResetKey] = useState(0);
  const [turnstileStatus, setTurnstileStatus] = useState(isTurnstileEnabled() ? 'loading' : 'disabled');
  const skillsPreview = useMemo(() => splitSkills(values.skills), [values.skills]);

  useEffect(() => {
    if (!edit.opportunity) return;
    const item = edit.opportunity;
    const details = item.internship_details || {};
    setValues({
      title: item.title || '',
      location: normalizeOptionValue(item.location, TUNISIAN_LOCATION_OPTIONS),
      availability: item.availability || 'On site',
      internship_type: normalizeInternshipType(details.internship_type),
      duration: normalizeOptionValue(details.duration, INTERNSHIP_DURATION_OPTIONS, '4_6_MONTHS'),
      start_date: normalizeDateInputValue(details.start_date),
      education_level: item.education_level || 'Bac+5',
      description: item.description || '',
      skills: Array.isArray(item.skills) ? item.skills.join(', ') : '',
      deadline: normalizeDateInputValue(item.deadline),
    });
  }, [edit.opportunity]);

  const updateValue = (field, value) => {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
    setSubmitError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setHasAttemptedSubmit(true);
    const validation = validateInternshipPostForm(values);
    setErrors(validation.errors);
    if (Object.keys(validation.errors).length > 0) return;
    if (isTurnstileEnabled() && !turnstileToken) {
      setSubmitError('Complete the anti-bot check before publishing.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError('');
    try {
      const payload = {
        ...buildPayload(values, validation.skills),
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
      setSubmitError(parsed.message || 'Unable to save this internship.');
      setTurnstileToken('');
      setTurnstileResetKey((value) => value + 1);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (edit.isLoading) {
    return <section className="flex min-h-[70vh] items-center justify-center text-sm text-neutral-600">Loading opportunity...</section>;
  }
  if (edit.loadError) {
    return <section className="flex min-h-[70vh] items-center justify-center px-4 text-center text-sm text-red-700">{edit.loadError}</section>;
  }

  return (
    <OpportunityPostLayout
      eyebrow={edit.isEditing ? 'Edit internship' : 'Create an internship'}
      title="Internship details"
      description={edit.isEditing ? 'Update the internship details. Changes are reviewed again before publication.' : 'Publish a trainee or student internship with the right duration and skills.'}
      headingId="publish-internship-heading"
    >
      <form onSubmit={handleSubmit} noValidate className="mt-10 flex flex-1 flex-col">
        <div className="flex-1 space-y-8">
          <FieldBlock className="border-t-0 pt-0">
            <label htmlFor="title" className="text-sm font-semibold text-neutral-900">Internship title *</label>
            <Input
              id="title"
              value={values.title}
              onChange={(event) => updateValue('title', event.target.value)}
              className={`mt-2 ${fieldClassName(errors.title)}`}
              aria-invalid={errors.title ? 'true' : 'false'}
              placeholder="Data Science Intern"
            />
            <FieldError message={errors.title} />
          </FieldBlock>

          <FieldBlock>
            <label htmlFor="location" className="text-sm font-semibold text-neutral-900">Location *</label>
            <p className="mt-1 text-sm text-neutral-500">Choose a Tunisian city or region from the approved list.</p>
            <Select value={values.location} onValueChange={(value) => updateValue('location', value)}>
              <SelectTrigger id="location" className={`mt-2 ${fieldClassName(errors.location)}`} aria-invalid={errors.location ? 'true' : 'false'}>
                <SelectValue placeholder="Select location" />
              </SelectTrigger>
              <SelectContent>
                {TUNISIAN_LOCATION_OPTIONS.map((item) => (
                  <SelectItem key={item} value={item}>{item}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FieldError message={errors.location} />
          </FieldBlock>

          <FieldBlock>
            <div className="grid gap-5 md:grid-cols-2">
              <div>
                <label htmlFor="internship_type" className="text-sm font-semibold text-neutral-900">Internship type *</label>
                <Select value={values.internship_type} onValueChange={(value) => updateValue('internship_type', value)}>
                  <SelectTrigger id="internship_type" className={`mt-2 ${fieldClassName(errors.internship_type)}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {INTERNSHIP_TYPE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.internship_type} />
              </div>

              <div>
                <label htmlFor="duration" className="text-sm font-semibold text-neutral-900">Duration *</label>
                <Select value={values.duration} onValueChange={(value) => updateValue('duration', value)}>
                  <SelectTrigger id="duration" className={`mt-2 ${fieldClassName(errors.duration)}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {INTERNSHIP_DURATION_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.duration} />
              </div>
            </div>
          </FieldBlock>

          <FieldBlock>
            <div className="grid gap-5 md:grid-cols-2">
              <div>
                <label htmlFor="start_date" className="text-sm font-semibold text-neutral-900">Start date *</label>
                <Input
                  id="start_date"
                  type="date"
                  value={values.start_date}
                  onChange={(event) => updateValue('start_date', event.target.value)}
                  className={`mt-2 ${fieldClassName(errors.start_date)}`}
                  aria-invalid={errors.start_date ? 'true' : 'false'}
                />
                <FieldError message={errors.start_date} />
              </div>

              <div>
                <label htmlFor="deadline" className="text-sm font-semibold text-neutral-900">Application deadline</label>
                <Input
                  id="deadline"
                  type="date"
                  value={values.deadline}
                  onChange={(event) => updateValue('deadline', event.target.value)}
                  className={`mt-2 ${fieldClassName(errors.deadline)}`}
                  aria-invalid={errors.deadline ? 'true' : 'false'}
                />
                <FieldError message={errors.deadline} />
              </div>
            </div>
          </FieldBlock>

          <FieldBlock>
            <div className="grid gap-5 md:grid-cols-2">
              <div>
                <label htmlFor="availability" className="text-sm font-semibold text-neutral-900">Work mode</label>
                <Select value={values.availability} onValueChange={(value) => updateValue('availability', value)}>
                  <SelectTrigger id="availability" className={`mt-2 ${fieldClassName(false)}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WORK_MODE_OPTIONS.map((item) => (
                      <SelectItem key={item} value={item}>{item}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label htmlFor="education_level" className="text-sm font-semibold text-neutral-900">Education level</label>
                <Select value={values.education_level} onValueChange={(value) => updateValue('education_level', value)}>
                  <SelectTrigger id="education_level" className={`mt-2 ${fieldClassName(false)}`}>
                    <SelectValue placeholder="Example: Bac+3" />
                  </SelectTrigger>
                  <SelectContent>
                    {INTERNSHIP_EDUCATION_OPTIONS.map((item) => (
                      <SelectItem key={item} value={item}>{item}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </FieldBlock>

          <FieldBlock>
            <label htmlFor="skills" className="text-sm font-semibold text-neutral-900">Skills</label>
            <Input
              id="skills"
              value={values.skills}
              onChange={(event) => updateValue('skills', event.target.value)}
              className={`mt-2 ${fieldClassName(errors.skills)}`}
              aria-invalid={errors.skills ? 'true' : 'false'}
              placeholder="Python, SQL, Excel"
            />
            <p className="mt-1 text-sm text-neutral-500">Separate skills with commas. Use up to 15.</p>
            <FieldError message={errors.skills} />
            {skillsPreview.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {skillsPreview.map((skill) => (
                  <span key={skill} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                    {skill}
                  </span>
                ))}
              </div>
            ) : null}
          </FieldBlock>

          <FieldBlock>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <label htmlFor="description" className="text-sm font-semibold text-neutral-900">Internship description *</label>
              <AiDescriptionDraftButton
                type="STAGE"
                title={values.title}
                contract="Internship"
                workMode={values.availability}
                location={values.location}
                skills={skillsPreview}
                educationLevel={values.education_level}
                deadline={values.deadline}
                currentDescription={values.description}
                onApply={(description) => updateValue('description', description)}
              />
            </div>
            <Textarea
              id="description"
              value={values.description}
              onChange={(event) => updateValue('description', event.target.value)}
              className={`mt-2 min-h-40 rounded-xl ${errors.description ? 'border-red-300' : ''}`}
              aria-invalid={errors.description ? 'true' : 'false'}
              placeholder="Describe the mission, expected learning outcomes, supervision, and application requirements."
            />
            <FieldError message={errors.description} />
          </FieldBlock>

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

        <div className="sticky bottom-0 mt-10 flex items-center justify-between border-t border-neutral-200 bg-white py-4">
          <Button type="button" variant="outline" asChild className="h-11 rounded-xl">
            <Link to="/organization/post">Back</Link>
          </Button>
          <Button type="submit" className="h-11 rounded-xl bg-blue-700 px-5 text-white hover:bg-blue-800" disabled={isSubmitting || (isTurnstileEnabled() && turnstileStatus !== 'verified')}>
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
            {isSubmitting ? (edit.isEditing ? 'Saving changes...' : 'Publishing...') : edit.isEditing ? 'Save changes' : 'Publish internship'}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </form>
    </OpportunityPostLayout>
  );
};

export default OrganizationInternshipPostPage;
