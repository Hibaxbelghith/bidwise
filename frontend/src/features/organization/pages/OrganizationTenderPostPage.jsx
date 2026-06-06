import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Loader2 } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select.jsx';
import { Textarea } from '../../../components/ui/textarea.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import { TUNISIAN_LOCATION_OPTIONS } from '../../profile/profilePreferences.js';
import { ErrorSummary, FieldBlock, FieldError, SubmitNotice, fieldClassName } from '../components/OpportunityPostFields.jsx';
import OpportunityPostLayout from '../components/OpportunityPostLayout.jsx';
import TenderDocumentsEditor from '../components/TenderDocumentsEditor.jsx';
import TenderLotsEditor from '../components/TenderLotsEditor.jsx';
import TurnstileChallenge, { isTurnstileEnabled } from '../components/TurnstileChallenge.jsx';
import { TENDER_DOCUMENT_TYPES, TENDER_PROCEDURE_OPTIONS } from '../opportunityPostConstants.js';
import { validateTenderPostForm } from '../opportunityPostValidation.js';
import { ORGANIZATION_OPPORTUNITY_SUBMITTED_PATH } from '../organizationFlow.js';
import {
  createOrganizationOpportunity,
  parseOrganizationApiError,
} from '../services/organizationService.js';

const createInitialValues = (buyer = '') => ({
  title: '',
  public_buyer: buyer,
  location: '',
  procedure: "Appel d'offres ouvert",
  deadline: '',
  deadline_time: '10:00',
  description: '',
  tender_number: '',
  number_of_lots: '',
  lot_type: '',
  price_character: '',
  delai_validite: '',
  execution_start_date: '',
  full_address: '',
  opening_date: '',
  opening_time: '',
  opening_address: '',
  evaluation_methodology: '',
  type_commande: '',
  financement: '',
  marche_cadre: false,
  marche_general: false,
  lots: [{ lot: 'Lot 1', objet: '', quantite: '', region: '', caution: '' }],
  documents: TENDER_DOCUMENT_TYPES.map((document) => ({
    type: document.value,
    label: document.label.replace(' URL', ''),
    url: '',
  })),
});

const ERROR_LABELS = {
  title: 'Tender title / Object',
  public_buyer: 'Public buyer',
  location: 'Execution region',
  procedure: 'Procedure',
  deadline: 'Deadline date',
  deadline_time: 'Deadline time',
  description: 'Description / scope',
  number_of_lots: 'Number of lots',
  delai_validite: 'Offer validity days',
  execution_start_date: 'Execution start date',
  opening_date: 'Opening date',
  opening_time: 'Opening hour',
  lots: 'Lots',
  documents: 'Documents',
};

const boolLabel = (value) => (value ? 'Yes' : 'No');

const buildPayload = (values, lots, documents) => ({
  type: 'PROJET',
  title: values.title.trim(),
  location: values.location,
  description: values.description.trim(),
  deadline: values.deadline,
  project_details: {
    public_buyer: values.public_buyer.trim(),
    region_execution: values.location,
    procedure: values.procedure.trim(),
    deadline_time: values.deadline_time,
    tender_number: values.tender_number.trim(),
    number_of_lots: values.number_of_lots.trim(),
    lot_type: values.lot_type.trim(),
    price_character: values.price_character.trim(),
    delai_validite: values.delai_validite.trim(),
    execution_start_date: values.execution_start_date || '',
    full_address: values.full_address.trim(),
    opening_date: values.opening_date || '',
    opening_time: values.opening_time || '',
    opening_address: values.opening_address.trim(),
    evaluation_methodology: values.evaluation_methodology.trim(),
    type_commande: values.type_commande.trim(),
    financement: values.financement.trim(),
    marche_cadre: values.marche_cadre,
    marche_general: values.marche_general,
    lots,
    documents,
  },
});

const OrganizationTenderPostPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const organizationName = user?.organization_profile?.organization_name || '';
  const [values, setValues] = useState(() => createInitialValues(organizationName));
  const [errors, setErrors] = useState({});
  const [step, setStep] = useState(1);
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState('');
  const [turnstileResetKey, setTurnstileResetKey] = useState(0);

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

  const validateCurrent = () => {
    const validation = validateTenderPostForm(values);
    setErrors(validation.errors);
    return validation;
  };

  const handleNext = () => {
    const validation = validateCurrent();
    const requiredKeys = ['title', 'public_buyer', 'location', 'procedure', 'deadline', 'deadline_time', 'description'];
    const stepErrors = requiredKeys.reduce((accumulator, key) => {
      if (validation.errors[key]) {
        accumulator[key] = validation.errors[key];
      }
      return accumulator;
    }, {});
    setErrors(stepErrors);
    if (Object.keys(stepErrors).length > 0) return;
    setStep(2);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (step === 1) {
      handleNext();
      return;
    }

    const validation = validateCurrent();
    if (Object.keys(validation.errors).length > 0) return;
    if (isTurnstileEnabled() && !turnstileToken) {
      setSubmitError('Complete the anti-bot check before publishing.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError('');
    try {
      await createOrganizationOpportunity({
        ...buildPayload(values, validation.lots, validation.documents),
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
      eyebrow="Create a call for tender"
      title={step === 1 ? 'Tender essentials' : 'Tender details'}
      description={step === 1 ? 'Capture the mandatory public tender information first.' : 'Add lots, documents, opening details, and additional procurement data.'}
      headingId="publish-tender-heading"
    >
      <form onSubmit={handleSubmit} className="mt-10 flex flex-1 flex-col">
        <div className="flex-1 space-y-8">
          {step === 1 ? (
            <>
              <FieldBlock className="border-t-0 pt-0">
                <label htmlFor="title" className="text-sm font-semibold text-neutral-900">Tender title / Object *</label>
                <Input id="title" value={values.title} onChange={(event) => updateValue('title', event.target.value)} className={`mt-2 ${fieldClassName(errors.title)}`} aria-invalid={errors.title ? 'true' : 'false'} />
                <FieldError message={errors.title} />
              </FieldBlock>

              <FieldBlock>
                <label htmlFor="public_buyer" className="text-sm font-semibold text-neutral-900">Public buyer *</label>
                <Input id="public_buyer" value={values.public_buyer} onChange={(event) => updateValue('public_buyer', event.target.value)} className={`mt-2 ${fieldClassName(errors.public_buyer)}`} aria-invalid={errors.public_buyer ? 'true' : 'false'} />
                <FieldError message={errors.public_buyer} />
              </FieldBlock>

              <FieldBlock>
                <label htmlFor="location" className="text-sm font-semibold text-neutral-900">Execution region *</label>
                <Select value={values.location} onValueChange={(value) => updateValue('location', value)}>
                  <SelectTrigger id="location" className={`mt-2 ${fieldClassName(errors.location)}`}>
                    <SelectValue placeholder="Select region" />
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
                <label htmlFor="procedure" className="text-sm font-semibold text-neutral-900">Procedure *</label>
                <Select value={values.procedure} onValueChange={(value) => updateValue('procedure', value)}>
                  <SelectTrigger id="procedure" className={`mt-2 ${fieldClassName(errors.procedure)}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TENDER_PROCEDURE_OPTIONS.map((item) => (
                      <SelectItem key={item} value={item}>{item}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.procedure} />
              </FieldBlock>

              <FieldBlock>
                <div className="grid gap-5 md:grid-cols-2">
                  <div>
                    <label htmlFor="deadline" className="text-sm font-semibold text-neutral-900">Deadline date *</label>
                    <Input id="deadline" type="date" value={values.deadline} onChange={(event) => updateValue('deadline', event.target.value)} className={`mt-2 ${fieldClassName(errors.deadline)}`} />
                    <FieldError message={errors.deadline} />
                  </div>
                  <div>
                    <label htmlFor="deadline_time" className="text-sm font-semibold text-neutral-900">Deadline time *</label>
                    <Input id="deadline_time" type="time" value={values.deadline_time} onChange={(event) => updateValue('deadline_time', event.target.value)} className={`mt-2 ${fieldClassName(errors.deadline_time)}`} />
                    <FieldError message={errors.deadline_time} />
                  </div>
                </div>
              </FieldBlock>

              <FieldBlock>
                <label htmlFor="description" className="text-sm font-semibold text-neutral-900">Description / scope *</label>
                <Textarea id="description" value={values.description} onChange={(event) => updateValue('description', event.target.value)} className={`mt-2 min-h-40 rounded-xl ${errors.description ? 'border-red-300' : ''}`} />
                <FieldError message={errors.description} />
              </FieldBlock>
            </>
          ) : (
            <>
              <FieldBlock className="border-t-0 pt-0">
                <div className="grid gap-5 md:grid-cols-2">
                  <div>
                    <label htmlFor="tender_number" className="text-sm font-semibold text-neutral-900">Tender number</label>
                    <Input id="tender_number" value={values.tender_number} onChange={(event) => updateValue('tender_number', event.target.value)} className={`mt-2 ${fieldClassName(false)}`} />
                  </div>
                  <div>
                    <label htmlFor="number_of_lots" className="text-sm font-semibold text-neutral-900">Number of lots</label>
                    <Input id="number_of_lots" inputMode="numeric" value={values.number_of_lots} onChange={(event) => updateValue('number_of_lots', event.target.value)} className={`mt-2 ${fieldClassName(errors.number_of_lots)}`} />
                    <FieldError message={errors.number_of_lots} />
                  </div>
                  <div>
                    <label htmlFor="lot_type" className="text-sm font-semibold text-neutral-900">Lot type</label>
                    <Input id="lot_type" value={values.lot_type} onChange={(event) => updateValue('lot_type', event.target.value)} className={`mt-2 ${fieldClassName(false)}`} />
                  </div>
                  <div>
                    <label htmlFor="price_character" className="text-sm font-semibold text-neutral-900">Price character</label>
                    <Input id="price_character" value={values.price_character} onChange={(event) => updateValue('price_character', event.target.value)} className={`mt-2 ${fieldClassName(false)}`} />
                  </div>
                  <div>
                    <label htmlFor="delai_validite" className="text-sm font-semibold text-neutral-900">Offer validity days</label>
                    <Input id="delai_validite" inputMode="numeric" value={values.delai_validite} onChange={(event) => updateValue('delai_validite', event.target.value)} className={`mt-2 ${fieldClassName(errors.delai_validite)}`} />
                    <FieldError message={errors.delai_validite} />
                  </div>
                  <div>
                    <label htmlFor="execution_start_date" className="text-sm font-semibold text-neutral-900">Execution start date</label>
                    <Input id="execution_start_date" type="date" value={values.execution_start_date} onChange={(event) => updateValue('execution_start_date', event.target.value)} className={`mt-2 ${fieldClassName(errors.execution_start_date)}`} />
                    <FieldError message={errors.execution_start_date} />
                  </div>
                </div>
              </FieldBlock>

              <FieldBlock>
                <div className="grid gap-5 md:grid-cols-2">
                  <div>
                    <label htmlFor="type_commande" className="text-sm font-semibold text-neutral-900">Order type</label>
                    <Input id="type_commande" value={values.type_commande} onChange={(event) => updateValue('type_commande', event.target.value)} className={`mt-2 ${fieldClassName(false)}`} />
                  </div>
                  <div>
                    <label htmlFor="financement" className="text-sm font-semibold text-neutral-900">Funding source</label>
                    <Input id="financement" value={values.financement} onChange={(event) => updateValue('financement', event.target.value)} className={`mt-2 ${fieldClassName(false)}`} />
                  </div>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  {[
                    ['marche_cadre', 'Framework contract'],
                    ['marche_general', 'General market'],
                  ].map(([field, label]) => (
                    <button key={field} type="button" onClick={() => updateValue(field, !values[field])} className="flex items-center justify-between rounded-xl border border-neutral-200 px-4 py-3 text-left text-sm hover:bg-neutral-50">
                      <span className="font-semibold text-neutral-900">{label}</span>
                      <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold text-neutral-700">{boolLabel(values[field])}</span>
                    </button>
                  ))}
                </div>
              </FieldBlock>

              <FieldBlock>
                <div className="grid gap-5 md:grid-cols-2">
                  <div>
                    <label htmlFor="opening_date" className="text-sm font-semibold text-neutral-900">Opening date</label>
                    <Input id="opening_date" type="date" value={values.opening_date} onChange={(event) => updateValue('opening_date', event.target.value)} className={`mt-2 ${fieldClassName(errors.opening_date)}`} />
                    <FieldError message={errors.opening_date} />
                  </div>
                  <div>
                    <label htmlFor="opening_time" className="text-sm font-semibold text-neutral-900">Opening hour</label>
                    <Input id="opening_time" type="time" value={values.opening_time} onChange={(event) => updateValue('opening_time', event.target.value)} className={`mt-2 ${fieldClassName(errors.opening_time)}`} />
                    <FieldError message={errors.opening_time} />
                  </div>
                  <div className="md:col-span-2">
                    <label htmlFor="full_address" className="text-sm font-semibold text-neutral-900">Reception address</label>
                    <Input id="full_address" value={values.full_address} onChange={(event) => updateValue('full_address', event.target.value)} className={`mt-2 ${fieldClassName(false)}`} />
                  </div>
                  <div className="md:col-span-2">
                    <label htmlFor="opening_address" className="text-sm font-semibold text-neutral-900">Opening address</label>
                    <Input id="opening_address" value={values.opening_address} onChange={(event) => updateValue('opening_address', event.target.value)} className={`mt-2 ${fieldClassName(false)}`} />
                  </div>
                  <div className="md:col-span-2">
                    <label htmlFor="evaluation_methodology" className="text-sm font-semibold text-neutral-900">Evaluation methodology</label>
                    <Input id="evaluation_methodology" value={values.evaluation_methodology} onChange={(event) => updateValue('evaluation_methodology', event.target.value)} className={`mt-2 ${fieldClassName(false)}`} />
                  </div>
                </div>
              </FieldBlock>

              <FieldBlock>
                <TenderLotsEditor lots={values.lots} error={errors.lots} onChange={(lots) => updateValue('lots', lots)} />
              </FieldBlock>

              <FieldBlock>
                <TenderDocumentsEditor documents={values.documents} error={errors.documents} onChange={(documents) => updateValue('documents', documents)} />
              </FieldBlock>
            </>
          )}

          <SubmitNotice
            message={submitError}
            tone={submitError.startsWith('Publishing limit reached') ? 'warning' : 'error'}
          />
          {step === 2 ? (
            <TurnstileChallenge
              onVerify={setTurnstileToken}
              onExpire={() => setTurnstileToken('')}
              resetSignal={turnstileResetKey}
            />
          ) : null}
          <ErrorSummary errors={errors} labels={ERROR_LABELS} />
        </div>

        <div className="sticky bottom-0 mt-10 flex items-center justify-between border-t border-neutral-200 bg-white py-4">
          <Button type="button" variant="outline" asChild={step === 1} onClick={step === 2 ? () => setStep(1) : undefined} className="h-11 rounded-xl">
            {step === 1 ? <Link to="/organization/post">Back</Link> : 'Back'}
          </Button>
          {step === 1 ? (
            <button
              type="button"
              onClick={handleNext}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-blue-700 px-5 text-sm font-medium text-white transition hover:bg-blue-800"
            >
              Continue
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </button>
          ) : (
            <Button type="submit" className="h-11 rounded-xl bg-blue-700 px-5 text-white hover:bg-blue-800" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
              Publish tender
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
        </div>
      </form>
    </OpportunityPostLayout>
  );
};

export default OrganizationTenderPostPage;
