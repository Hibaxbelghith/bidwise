import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Loader2 } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select.jsx';
import { Textarea } from '../../../components/ui/textarea.jsx';
import { TUNISIAN_LOCATION_OPTIONS } from '../../profile/profilePreferences.js';
import OpportunityPostLayout from '../components/OpportunityPostLayout.jsx';
import { ErrorSummary, FieldBlock, FieldError, SubmitNotice, fieldClassName } from '../components/OpportunityPostFields.jsx';
import TurnstileChallenge, { isTurnstileEnabled } from '../components/TurnstileChallenge.jsx';
import {
  SEASON_OPTIONS,
  WORK_MODE_OPTIONS,
} from '../opportunityPostConstants.js';
import { splitSkills, validateSeasonalPostForm } from '../opportunityPostValidation.js';
import { ORGANIZATION_OPPORTUNITY_SUBMITTED_PATH } from '../organizationFlow.js';
import {
  createOrganizationOpportunity,
  parseOrganizationApiError,
} from '../services/organizationService.js';

const INITIAL_VALUES = {
  title: '',
  location: '',
  availability: 'On site',
  season: 'SUMMER',
  start_date: '',
  end_date: '',
  description: '',
  skills: '',
  salary: '',
  deadline: '',
};

const ERROR_LABELS = {
  title: 'Seasonal job title',
  location: 'Location',
  season: 'Season',
  start_date: 'Start date',
  end_date: 'End date',
  description: 'Seasonal job description',
  skills: 'Skills',
  salary: 'Salary',
  deadline: 'Application deadline',
};

const buildPayload = (values, skills) => ({
  type: 'SAISONNIER',
  title: values.title.trim(),
  location: values.location,
  description: values.description.trim(),
  contract: 'Seasonal',
  availability: values.availability,
  salary: values.salary.trim(),
  skills,
  deadline: values.deadline || null,
  seasonal_details: {
    season: values.season,
    start_date: values.start_date,
    end_date: values.end_date,
  },
});

const OrganizationSeasonalPostPage = () => {
  const navigate = useNavigate();
  const [values, setValues] = useState(INITIAL_VALUES);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState('');
  const [turnstileResetKey, setTurnstileResetKey] = useState(0);
  const skillsPreview = useMemo(() => splitSkills(values.skills), [values.skills]);

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
    const validation = validateSeasonalPostForm(values);
    setErrors(validation.errors);
    if (Object.keys(validation.errors).length > 0) return;
    if (isTurnstileEnabled() && !turnstileToken) {
      setSubmitError('Complete the anti-bot check before publishing.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError('');
    try {
      await createOrganizationOpportunity({
        ...buildPayload(values, validation.skills),
        turnstile_token: turnstileToken,
      });
      navigate(ORGANIZATION_OPPORTUNITY_SUBMITTED_PATH, { replace: true });
    } catch (error) {
      setSubmitError(parseOrganizationApiError(error).message);
      setTurnstileToken('');
      setTurnstileResetKey((value) => value + 1);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <OpportunityPostLayout
      eyebrow="Create a seasonal job"
      title="Seasonal job details"
      description="Publish temporary work for seasonal demand, events, holidays, or short operational needs."
      headingId="publish-seasonal-heading"
    >
      <form onSubmit={handleSubmit} className="mt-10 flex flex-1 flex-col">
        <div className="flex-1 space-y-8">
          <FieldBlock className="border-t-0 pt-0">
            <label htmlFor="title" className="text-sm font-semibold text-neutral-900">Seasonal job title *</label>
            <Input
              id="title"
              value={values.title}
              onChange={(event) => updateValue('title', event.target.value)}
              className={`mt-2 ${fieldClassName(errors.title)}`}
              aria-invalid={errors.title ? 'true' : 'false'}
              placeholder="Summer Event Assistant"
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
                <label htmlFor="season" className="text-sm font-semibold text-neutral-900">Season *</label>
                <Select value={values.season} onValueChange={(value) => updateValue('season', value)}>
                  <SelectTrigger id="season" className={`mt-2 ${fieldClassName(errors.season)}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SEASON_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.season} />
              </div>

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
                <label htmlFor="end_date" className="text-sm font-semibold text-neutral-900">End date *</label>
                <Input
                  id="end_date"
                  type="date"
                  value={values.end_date}
                  onChange={(event) => updateValue('end_date', event.target.value)}
                  className={`mt-2 ${fieldClassName(errors.end_date)}`}
                  aria-invalid={errors.end_date ? 'true' : 'false'}
                />
                <FieldError message={errors.end_date} />
              </div>
            </div>
          </FieldBlock>

          <FieldBlock>
            <label htmlFor="description" className="text-sm font-semibold text-neutral-900">Seasonal job description *</label>
            <Textarea
              id="description"
              value={values.description}
              onChange={(event) => updateValue('description', event.target.value)}
              className={`mt-2 min-h-40 rounded-xl ${errors.description ? 'border-red-300' : ''}`}
              aria-invalid={errors.description ? 'true' : 'false'}
              placeholder="Describe the work period, daily tasks, schedule expectations, and candidate requirements."
            />
            <FieldError message={errors.description} />
          </FieldBlock>

          <FieldBlock>
            <div className="grid gap-5 md:grid-cols-2">
              <div>
                <label htmlFor="salary" className="text-sm font-semibold text-neutral-900">Salary</label>
                <Input
                  id="salary"
                  value={values.salary}
                  onChange={(event) => updateValue('salary', event.target.value)}
                  className={`mt-2 ${fieldClassName(errors.salary)}`}
                  aria-invalid={errors.salary ? 'true' : 'false'}
                  placeholder="900 TND"
                />
                <FieldError message={errors.salary} />
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
            <label htmlFor="skills" className="text-sm font-semibold text-neutral-900">Skills</label>
            <Input
              id="skills"
              value={values.skills}
              onChange={(event) => updateValue('skills', event.target.value)}
              className={`mt-2 ${fieldClassName(errors.skills)}`}
              aria-invalid={errors.skills ? 'true' : 'false'}
              placeholder="Customer service, Inventory, English"
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

          <SubmitNotice
            message={submitError}
            tone={submitError.startsWith('Publishing limit reached') ? 'warning' : 'error'}
          />
          <TurnstileChallenge
            onVerify={setTurnstileToken}
            onExpire={() => setTurnstileToken('')}
            resetSignal={turnstileResetKey}
          />
          <ErrorSummary errors={errors} labels={ERROR_LABELS} />
        </div>

        <div className="sticky bottom-0 mt-10 flex items-center justify-between border-t border-neutral-200 bg-white py-4">
          <Button type="button" variant="outline" asChild className="h-11 rounded-xl">
            <Link to="/organization/post">Back</Link>
          </Button>
          <Button type="submit" className="h-11 rounded-xl bg-blue-700 px-5 text-white hover:bg-blue-800" disabled={isSubmitting}>
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
            Publish seasonal job
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </form>
    </OpportunityPostLayout>
  );
};

export default OrganizationSeasonalPostPage;
