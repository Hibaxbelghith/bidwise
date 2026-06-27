import * as Dialog from '@radix-ui/react-dialog';
import { Briefcase, Check, FileText, Loader2, Mail, MapPin, Phone, Upload, X, Calendar, Building2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { Button } from '../../../../components/ui/button.jsx';
import { Input } from '../../../../components/ui/input.jsx';
import { Label } from '../../../../components/ui/label.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import {
  submitOrganizationApplication,
  uploadApplicationCoverLetter,
  uploadProfileResume,
} from '../../services/opportunitiesService.js';

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const RESUME_EXTENSIONS = ['pdf', 'docx', 'doc', 'rtf', 'txt'];
const COVER_LETTER_EXTENSIONS = ['pdf', 'docx'];

const getFileExtension = (file) => String(file?.name || '').split('.').pop()?.toLowerCase() || '';
const getResumeName = (resume) => (
  resume?.metadata?.original_filename
  || String(resume?.file_url || '').split('/').pop()
  || 'Profile resume'
);

const getApiMessage = (error, fallback, t) => {
  const data = error?.response?.data;
  if (error?.response?.status === 409) return t('opportunities.detail.alreadyApplied');
  if (data?.cv_id?.[0]) return t('opportunities.detail.selectResumeBeforeSubmit');
  if (data?.contact_email?.[0]) return data.contact_email[0];
  if (data?.contact_phone?.[0]) return data.contact_phone[0];
  if (data?.cover_letter_url?.[0]) return data.cover_letter_url[0];
  return data?.detail || fallback;
};

const validateFile = (file, extensions, label, t) => {
  if (!file) return t('opportunities.detail.chooseFileFirst', { label: label.toLowerCase() });
  if (!extensions.includes(getFileExtension(file))) {
    return t('opportunities.detail.fileMustBe', {
      label,
      extensions: extensions.map((item) => item.toUpperCase()).join(' or '),
    });
  }
  if (file.size > MAX_FILE_SIZE) return t('opportunities.detail.fileMaxSize', { label });
  return '';
};

const FileRow = ({ name, onRemove }) => (
  <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
    <FileText className="h-4 w-4 text-blue-600" />
    <span className="flex-1 truncate text-sm text-gray-700">{name}</span>
    {onRemove && (
      <button
        type="button"
        onClick={onRemove}
        className="rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    )}
  </div>
);

const OpportunityApplicationDialog = ({
  open,
  onOpenChange,
  opportunity,
  organizationLabel,
  user,
  onSubmitted,
  onUserRefresh,
}) => {
  const { t } = useLanguage();
  const resumeInputRef = useRef(null);
  const coverLetterInputRef = useRef(null);
  const profileResume = user?.profil?.active_resume || null;
  const [resume, setResume] = useState(profileResume);
  const [showResumeUpload, setShowResumeUpload] = useState(false);
  const [contactEmail, setContactEmail] = useState(user?.email || '');
  const [contactPhone, setContactPhone] = useState('');
  const [coverLetter, setCoverLetter] = useState(null);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [uploadingCoverLetter, setUploadingCoverLetter] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    const active = user?.profil?.active_resume || null;
    setResume(active);
    setShowResumeUpload(!active);
    setContactEmail(user?.email || '');
    setContactPhone('');
    setCoverLetter(null);
    setError('');
  }, [open, user]);

  const handleResumeUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    const validationError = validateFile(file, RESUME_EXTENSIONS, t('opportunities.detail.resume'), t);
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setError('');
      setUploadingResume(true);
      const result = await uploadProfileResume(file, { activate: true });
      const uploaded = result.resume || null;
      setResume(uploaded);
      setShowResumeUpload(false);
      await onUserRefresh?.();
    } catch (uploadError) {
      setError(getApiMessage(uploadError, t('opportunities.detail.unableUploadResume'), t));
    } finally {
      setUploadingResume(false);
    }
  };

  const handleCoverLetterUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    const validationError = validateFile(file, COVER_LETTER_EXTENSIONS, t('opportunities.detail.coverLetter'), t);
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setError('');
      setUploadingCoverLetter(true);
      const result = await uploadApplicationCoverLetter(file);
      setCoverLetter({ name: result.name || file.name, url: result.url });
    } catch (uploadError) {
      setError(getApiMessage(uploadError, t('opportunities.detail.unableUploadCoverLetter'), t));
    } finally {
      setUploadingCoverLetter(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!resume?.id) {
      setError(t('opportunities.detail.selectResumeBeforeSubmit'));
      return;
    }
    if (!contactEmail.trim()) {
      setError(t('opportunities.detail.emailRequired'));
      return;
    }

    try {
      setError('');
      setSubmitting(true);
      const result = await submitOrganizationApplication(opportunity.id, {
        cv_id: resume.id,
        cover_letter_url: coverLetter?.url || '',
        contact_email: contactEmail.trim(),
        contact_phone: contactPhone.trim(),
      });
      onSubmitted(result);
    } catch (submitError) {
      setError(getApiMessage(submitError, t('opportunities.detail.unableSubmitApplication'), t));
    } finally {
      setSubmitting(false);
    }
  };

  const isBusy = uploadingResume || uploadingCoverLetter || submitting;

  // Format deadline if exists
  const deadline = opportunity.deadline ? new Date(opportunity.deadline).toLocaleDateString() : null;
  const location = opportunity.location || opportunity.remotes?.[0]?.display_value || null;

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => !isBusy && onOpenChange(nextOpen)}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[80] bg-black/40" />
        <Dialog.Content className="fixed inset-x-0 bottom-0 z-[81] max-h-[90vh] overflow-y-auto rounded-t-xl bg-white shadow-xl sm:inset-auto sm:left-1/2 sm:top-1/2 sm:w-[min(92vw,520px)] sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-xl">
          {/* Header - Clear opportunity info */}
          <div className="border-b border-gray-100 px-5 py-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <Dialog.Title className="text-lg font-semibold text-gray-900">
                  {opportunity.title}
                </Dialog.Title>
                <div className="mt-1 flex items-center gap-2 text-sm text-gray-500">
                  <Building2 className="h-3.5 w-3.5" />
                  <span>{organizationLabel || opportunity.organization_name || t('opportunities.detail.organization')}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-400">
                  {location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {location}
                    </span>
                  )}
                  {deadline && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {t('opportunities.detail.deadlineLabel', { date: deadline })}
                    </span>
                  )}
                </div>
              </div>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                  disabled={isBusy}
                >
                  <X className="h-4 w-4" />
                </button>
              </Dialog.Close>
            </div>
          </div>

          <div className="p-5">
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Resume */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-gray-700">{t('opportunities.detail.resumeRequired')}</Label>
                <p className="text-xs text-gray-400">{t('opportunities.detail.resumeFormats')}</p>

                {resume?.id && !showResumeUpload ? (
                  <div className="space-y-2">
                    <FileRow name={getResumeName(resume)} />
                    <button
                      type="button"
                      className="text-xs text-blue-600 hover:underline"
                      onClick={() => setShowResumeUpload(true)}
                      disabled={isBusy}
                    >
                      {t('opportunities.detail.useDifferentResume')}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => resumeInputRef.current?.click()}
                      disabled={isBusy}
                      className="w-full"
                    >
                      {uploadingResume ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                      {uploadingResume ? t('profile.saving') : t('opportunities.detail.uploadResume')}
                    </Button>
                    {profileResume && showResumeUpload && (
                      <button
                        type="button"
                        className="text-xs text-blue-600 hover:underline"
                        onClick={() => { setResume(profileResume); setShowResumeUpload(false); }}
                      >
                        {t('opportunities.detail.useProfileResume')}
                      </button>
                    )}
                  </div>
                )}
                <input
                  ref={resumeInputRef}
                  type="file"
                  accept=".pdf,.docx,.doc,.rtf,.txt"
                  className="hidden"
                  onChange={handleResumeUpload}
                />
              </div>

              {/* Contact */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1">
                  <Label htmlFor="email" className="text-sm font-medium text-gray-700">{t('opportunities.detail.emailRequiredLabel')}</Label>
                  <Input
                    id="email"
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    disabled={isBusy}
                    className="h-9"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="phone" className="text-sm font-medium text-gray-700">{t('opportunities.detail.phone')}</Label>
                  <Input
                    id="phone"
                    type="tel"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    placeholder="+216 12 345 678"
                    disabled={isBusy}
                    className="h-9"
                  />
                </div>
              </div>

              {/* Cover Letter */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-gray-700">{t('opportunities.detail.coverLetter')}</Label>
                <p className="text-xs text-gray-400">{t('opportunities.detail.coverLetterFormats')}</p>
                {coverLetter ? (
                  <FileRow name={coverLetter.name} onRemove={() => setCoverLetter(null)} />
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => coverLetterInputRef.current?.click()}
                    disabled={isBusy}
                    className="w-full"
                  >
                    {uploadingCoverLetter ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                    {uploadingCoverLetter ? t('profile.saving') : t('opportunities.detail.attachCoverLetter')}
                  </Button>
                )}
                <input
                  ref={coverLetterInputRef}
                  type="file"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={handleCoverLetterUpload}
                />
              </div>

              {/* Error */}
              {error && (
                <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                  {error}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={isBusy}
                  className="flex-1"
                >
                  {t('common.cancel')}
                </Button>
                <Button
                  type="submit"
                  disabled={!resume?.id || isBusy}
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  {submitting ? t('opportunities.detail.submitting') : t('opportunities.detail.submit')}
                </Button>
              </div>
            </form>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};

export default OpportunityApplicationDialog;
