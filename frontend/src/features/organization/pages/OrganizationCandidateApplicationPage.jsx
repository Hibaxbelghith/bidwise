import { useEffect, useLayoutEffect, useState } from 'react';
import { useParams, Navigate, Link } from 'react-router-dom';
import {
  ChevronLeft,
  Check,
  FileText,
  Download,
  User,
  MapPin,
  Mail,
  Phone,
  Briefcase,
  Wrench,
  AlignLeft,
  Star,
  Trash2,
  X,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';

import { Spinner } from '../../../components/ui/spinner.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import {
  acceptApplication,
  deleteApplication,
  getCandidateApplicationProfile,
  rejectApplication,
} from '../services/organizationService.js';
import {
  BUSINESS_FAMILY_OPTIONS,
  EMPLOYMENT_TYPE_OPTIONS,
  WORK_MODE_OPTIONS,
} from '../../profile/profilePreferences.js';
import { getApplicationStatusMeta } from '../../applications/applicationStatusUi.js';

/* ─── helpers ─────────────────────────────────────────────────────────────── */

const WORK_MODE_LABELS = Object.fromEntries(WORK_MODE_OPTIONS.map((item) => [item.value, item.label]));
const EMPLOYMENT_TYPE_LABELS = Object.fromEntries(EMPLOYMENT_TYPE_OPTIONS.map((item) => [item.value, item.label]));
const INTEREST_LABELS = Object.fromEntries(BUSINESS_FAMILY_OPTIONS.map((item) => [item.value, item.label]));

const labelFromMap = (value, labels) => (
  labels[value] || String(value || '').replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
);

const hasCompensation = (compensation) => Boolean(compensation && (compensation.min || compensation.max));

const formatCompensation = (compensation) => {
  if (!hasCompensation(compensation)) return '';
  const period = compensation.period ? labelFromMap(compensation.period, {
    MONTHLY: 'month',
    YEARLY: 'year',
    DAILY: 'day',
    HOURLY: 'hour',
  }) : '';
  const suffix = `${compensation.currency || 'TND'}${period ? `/${period}` : ''}`;
  if (compensation.min && compensation.max) return `${compensation.min} - ${compensation.max} ${suffix}`;
  if (compensation.min) return `From ${compensation.min} ${suffix}`;
  return `Up to ${compensation.max} ${suffix}`;
};

const buildContactMailto = ({ email, candidateName, opportunityTitle }) => {
  const recipient = String(email || '').trim();
  if (!recipient) return '';

  const title = String(opportunityTitle || 'your application').trim();
  const safeCandidateName = String(candidateName || 'Candidate').trim();
  const subject = `Regarding your application - ${title}`;
  const body = [
    `Hello ${safeCandidateName},`,
    '',
    `Thank you for your application for "${title}" on BidWise.`,
    'We would like to get in touch with you regarding the next steps.',
    '',
    'Best regards,',
    'BidWise Organization Team',
  ].join('\n');

  return `mailto:${encodeURIComponent(recipient)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
};

const StatusBadge = ({ statut }) => {
  const { label, textColor } = getApplicationStatusMeta(statut, 'organization');
  const className = statut === 'REJECTED'
    ? 'bg-red-50'
    : statut === 'SUBMITTED'
      ? 'bg-blue-50'
      : 'bg-neutral-100';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${className} ${textColor}`}>
      {label}
    </span>
  );
};

/* ─── collapsible section ─────────────────────────────────────────────────── */

const Section = ({ icon: Icon, title, defaultOpen = true, children }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-neutral-50 transition-colors"
      >
        <span className="flex items-center gap-2.5 text-sm font-medium text-neutral-800">
          <Icon className="h-4 w-4 text-neutral-400" />
          {title}
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 text-neutral-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-neutral-400" />
        )}
      </button>
      {open && (
        <>
          <div className="border-t border-neutral-100" />
          <div className="px-6 py-5">{children}</div>
        </>
      )}
    </div>
  );
};

/* ─── experience item ─────────────────────────────────────────────────────── */

const ExpItem = ({ icon: Icon, role, company, period, location, bullets }) => (
  <div className="flex gap-4 py-4 first:pt-0 last:pb-0 [&+&]:border-t [&+&]:border-neutral-100">
    <div className="flex-shrink-0 w-9 h-9 rounded-lg border border-neutral-200 bg-neutral-50 flex items-center justify-center">
      <Icon className="h-4 w-4 text-neutral-400" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-sm font-medium text-neutral-900">{role}</p>
      {company && <p className="text-sm text-neutral-500 mt-0.5">{company}</p>}
      <p className="text-xs text-neutral-400 mt-0.5">
        {period}{location ? ` · ${location}` : ''}
      </p>
      {bullets?.length > 0 && (
        <ul className="mt-2.5 space-y-1 list-disc list-inside">
          {bullets.map((b, i) => (
            <li key={i} className="text-xs text-neutral-500 leading-relaxed">{b}</li>
          ))}
        </ul>
      )}
    </div>
  </div>
);

/* ─── document link ───────────────────────────────────────────────────────── */

const DocLink = ({ href, label, color = 'blue' }) => {
  const colorMap = { blue: 'text-blue-600', green: 'text-green-600' };
  if (!href) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3.5 opacity-60">
        <FileText className="h-5 w-5 text-neutral-400 shrink-0" />
        <span className="text-sm text-neutral-500">Not provided</span>
      </div>
    );
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white p-3.5 hover:bg-neutral-50 transition-colors"
    >
      <FileText className={`h-5 w-5 shrink-0 ${colorMap[color]}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-900">{label}</p>
        <p className="text-xs text-neutral-500">Open file</p>
      </div>
      <Download className="h-4 w-4 text-neutral-400 shrink-0" />
    </a>
  );
};

/* ─── sidebar ─────────────────────────────────────────────────────────────── */

const CandidateSidebar = ({ data }) => (
  <div className="space-y-3">
    {/* Documents */}
    <div className="bg-white border border-neutral-200 rounded-xl p-4">
      <p className="text-[11px] font-medium uppercase tracking-widest text-neutral-400 mb-3">Documents</p>
      <div className="space-y-2">
        <DocLink href={data.cv_url} label="Resume / CV" color="blue" />
        <DocLink href={data.cover_letter_url} label="Cover Letter" color="green" />
      </div>
    </div>

    {/* Application summary */}
    <div className="bg-white border border-neutral-200 rounded-xl p-4">
      <p className="text-[11px] font-medium uppercase tracking-widest text-neutral-400 mb-3">Application</p>
      <div className="divide-y divide-neutral-100 text-sm">
        <div className="flex justify-between items-start py-2.5 gap-3">
          <span className="text-neutral-400 shrink-0">Position</span>
          <span className="font-medium text-neutral-800 text-right">{data.opportunity?.title}</span>
        </div>
        <div className="flex justify-between items-center py-2.5">
          <span className="text-neutral-400">Location</span>
          <span className="text-neutral-700">{data.opportunity?.location}</span>
        </div>
        <div className="flex justify-between items-center py-2.5">
          <span className="text-neutral-400">Status</span>
          <StatusBadge statut={data.statut} />
        </div>
      </div>
    </div>
  </div>
);

/* ─── main content ────────────────────────────────────────────────────────── */

const CandidateProfileContent = ({ data }) => {
  return (
    <div className="px-5 py-5">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-4 items-start">
        {/* Left column */}
        <div className="space-y-3 min-w-0">
          {/* Hero card */}
          <div className="bg-white border border-neutral-200 rounded-xl p-6">
            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h2 className="text-xl font-semibold text-neutral-900">{data.candidate_name}</h2>
                <StatusBadge statut={data.statut} />
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3">
                <span className="flex items-center gap-1.5 text-xs text-neutral-500">
                  <Mail className="h-3.5 w-3.5" />{data.candidate_email}
                </span>
                {data.contact_phone && (
                  <span className="flex items-center gap-1.5 text-xs text-neutral-500">
                    <Phone className="h-3.5 w-3.5" />{data.contact_phone}
                  </span>
                )}
              </div>
              {data.opportunity?.title && (
                <p className="flex items-center gap-1.5 text-xs text-neutral-500 mt-2.5">
                  <Briefcase className="h-3.5 w-3.5" />
                  Applied for&nbsp;
                  <span className="font-medium text-neutral-700">{data.opportunity.title}</span>
                </p>
              )}
            </div>
          </div>

          {/* Professional Summary */}
          {data.profile?.summary && (
            <Section icon={AlignLeft} title="Professional Summary">
              <p className="text-sm text-neutral-600 leading-relaxed">{data.profile.summary}</p>
            </Section>
          )}

          {/* Experience */}
          {data.profile?.years_experience && (
            <Section icon={Briefcase} title="Experience">
              <ExpItem
                icon={Briefcase}
                role={data.profile?.target_roles?.[0] ?? 'Work experience'}
                period={`${data.profile.years_experience} years`}
              />
            </Section>
          )}

          {/* Skills */}
          {(data.profile?.skills?.length > 0 || data.profile?.resume_skills?.length > 0) && (
            <Section icon={Wrench} title="Skills">
              <div className="flex flex-wrap gap-2">
                {[...(data.profile.skills ?? []), ...(data.profile.resume_skills ?? [])].map(
                  (skill, i) => (
                    <span
                      key={i}
                      className="inline-flex px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-medium"
                    >
                      {skill}
                    </span>
                  )
                )}
              </div>
            </Section>
          )}

          {/* Preferences */}
          {(data.profile?.work_mode_preferences?.length > 0 ||
            data.profile?.employment_types?.length > 0 ||
            data.profile?.preferred_locations?.length > 0 ||
            hasCompensation(data.profile?.compensation)) && (
            <Section icon={MapPin} title="Preferences" defaultOpen={false}>
              <div className="grid sm:grid-cols-2 gap-5 text-sm">
                {data.profile.preferred_locations?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-2">Preferred Locations</p>
                    <ul className="space-y-1">
                      {data.profile.preferred_locations.map((loc, i) => (
                        <li key={i} className="text-neutral-600 flex items-center gap-1.5">
                          <MapPin className="h-3 w-3 text-neutral-400" />{loc}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.profile.work_mode_preferences?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-2">Work Mode</p>
                    <ul className="space-y-1">
                      {data.profile.work_mode_preferences.map((mode, i) => (
                        <li key={i} className="text-neutral-600">- {labelFromMap(mode, WORK_MODE_LABELS)}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.profile.employment_types?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-2">Employment Types</p>
                    <ul className="space-y-1">
                      {data.profile.employment_types.map((type, i) => (
                        <li key={i} className="text-neutral-600">- {labelFromMap(type, EMPLOYMENT_TYPE_LABELS)}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {hasCompensation(data.profile.compensation) && (
                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-2">Salary Expectations</p>
                    <p className="text-neutral-600">{formatCompensation(data.profile.compensation)}</p>
                  </div>
                )}
              </div>
            </Section>
          )}

          {/* Interests */}
          {data.profile?.interests?.length > 0 && (
            <Section icon={Star} title="Interests" defaultOpen={false}>
              <div className="flex flex-wrap gap-2">
                {data.profile.interests.map((item, i) => (
                  <span
                    key={i}
                    className="inline-flex px-3 py-1 rounded-full bg-amber-50 text-amber-700 text-xs font-medium"
                  >
                    {labelFromMap(item, INTEREST_LABELS)}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* Profile not shared fallback */}
          {!data.profile_visible && (
            <div className="bg-white border border-neutral-200 rounded-xl p-8 text-center">
              <User className="h-10 w-10 text-neutral-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-neutral-600">Profile Not Shared</p>
              <p className="text-xs text-neutral-400 mt-1">
                This candidate has not shared their profile.
              </p>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <CandidateSidebar data={data} />
      </div>
    </div>
  );
};

/* ─── page ────────────────────────────────────────────────────────────────── */

const OrganizationCandidateApplicationPage = () => {
  const { loading, user } = useAuth();
  const profile = user?.organization_profile;
  const { applicationId } = useParams();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionId, setActionId] = useState('');
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [restoreStatus, setRestoreStatus] = useState(null);

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, []);

  useEffect(() => {
    let isCancelled = false;
    if (!isOrganizationProfileComplete(profile)) return undefined;

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError('');
        const result = await getCandidateApplicationProfile(applicationId);
        if (!isCancelled) setData(result);
      } catch (err) {
        if (!isCancelled) {
          setError(err?.response?.data?.detail || 'Unable to load candidate profile.');
          console.error('Error fetching candidate profile:', err);
        }
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    };

    fetchData();
    return () => { isCancelled = true; };
  }, [profile, applicationId]);

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-neutral-50 px-4">
        <div className="rounded-lg border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-600">
          Loading organization workspace…
        </div>
      </section>
    );
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  const updateStatus = async (action) => {
    if (!data?.opportunity?.id || !data?.id) return;
    setActionError('');
    setActionId(action);
    try {
      const request = action === 'accept' ? acceptApplication : rejectApplication;
      const currentStatus = data.statut;
      const shouldRestoreAccept =
        action === 'accept' &&
        currentStatus === 'SHORTLISTED' &&
        (restoreStatus === 'SUBMITTED' || restoreStatus === 'VIEWED_BY_ORGANIZATION');
      const shouldRestoreReject =
        action === 'reject' &&
        currentStatus === 'REJECTED' &&
        (restoreStatus === 'SUBMITTED' || restoreStatus === 'VIEWED_BY_ORGANIZATION');

      const result = await request(data.opportunity.id, data.id, {
        restoreStatus: shouldRestoreAccept || shouldRestoreReject ? restoreStatus : undefined,
      });

      setData((current) =>
        current
          ? {
              ...current,
              statut: result?.status || current.statut,
            }
          : current
      );

      if (result?.status === 'SHORTLISTED' || result?.status === 'REJECTED') {
        if (currentStatus === 'SUBMITTED' || currentStatus === 'VIEWED_BY_ORGANIZATION') {
          setRestoreStatus(currentStatus);
        }
      } else if (result?.status === 'SUBMITTED' || result?.status === 'VIEWED_BY_ORGANIZATION') {
        setRestoreStatus(null);
      }
    } catch (err) {
      setActionError(err?.response?.data?.detail || 'Unable to update application.');
    } finally {
      setActionId('');
    }
  };

  const removeApplication = async () => {
    if (!data?.opportunity?.id || !data?.id) return;
    setActionError('');
    setActionId('delete');
    try {
      await deleteApplication(data.opportunity.id, data.id);
      setDeleteConfirmOpen(false);
      window.history.back();
    } catch (err) {
      setActionError(err?.response?.data?.detail || 'Unable to delete application.');
    } finally {
      setActionId('');
    }
  };

  const contactEmail = String(data?.contact_email || data?.candidate_email || '').trim();
  const contactMailto = buildContactMailto({
    email: contactEmail,
    candidateName: data?.candidate_name,
    opportunityTitle: data?.opportunity?.title,
  });

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-[#f4f3f1]" aria-labelledby="candidate-heading">
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[auto_1fr]">
        <OrganizationSidebar
          activePath="/organization/applications"
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed((v) => !v)}
        />

        <div className="min-w-0">
          {/* Header */}
          <div className="border-b border-neutral-200 bg-[#efeeec] px-5 py-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <Link
                  to="/organization/applications"
                  className="flex items-center justify-center w-9 h-9 rounded-lg hover:bg-neutral-200 transition-colors"
                  title="Back to applications"
                >
                  <ChevronLeft className="h-5 w-5 text-neutral-700" />
                </Link>
                <h1 id="candidate-heading" className="text-xl font-semibold text-neutral-900">
                  Candidate Profile
                </h1>
              </div>
              {data ? (
                <div className="flex flex-wrap items-center gap-2">
                  {contactMailto ? (
                    <a
                      href={contactMailto}
                      className="inline-flex h-10 items-center gap-2 rounded-lg border border-neutral-300 bg-white px-3 text-sm font-medium text-neutral-800 hover:bg-neutral-50"
                    >
                      <Mail className="h-4 w-4" />
                      Contact
                    </a>
                  ) : null}
                  <button
                    type="button"
                    disabled={actionId === 'accept' || data.statut === 'WITHDRAWN'}
                    onClick={() => updateStatus('accept')}
                    className="inline-flex h-10 items-center gap-2 rounded-lg border border-neutral-300 bg-white px-3 text-sm font-medium text-neutral-800 hover:bg-neutral-50 disabled:opacity-50"
                  >
                    <Check className="h-4 w-4" />
                    {data.statut === 'SHORTLISTED' && restoreStatus ? 'Undo preselection' : 'Preselect'}
                  </button>
                  <button
                    type="button"
                    disabled={actionId === 'reject' || data.statut === 'WITHDRAWN'}
                    onClick={() => updateStatus('reject')}
                    className="inline-flex h-10 items-center gap-2 rounded-lg border border-neutral-300 bg-white px-3 text-sm font-medium text-neutral-800 hover:bg-neutral-50 disabled:opacity-50"
                  >
                    <X className="h-4 w-4" />
                    {data.statut === 'REJECTED' && restoreStatus ? 'Undo rejection' : 'Reject'}
                  </button>
                  <button
                    type="button"
                    disabled={actionId === 'delete'}
                    onClick={() => setDeleteConfirmOpen(true)}
                    className="inline-flex h-10 items-center gap-2 rounded-lg border border-red-200 bg-white px-3 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4" />
                    Remove
                  </button>
                </div>
              ) : null}
            </div>
          </div>

          {/* Body */}
          <div className="rounded-tl-xl bg-[#f4f3f1]">
            {actionError ? (
              <div className="mx-5 mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {actionError}
              </div>
            ) : null}
            {error ? (
              <div className="mx-5 mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            ) : isLoading ? (
              <div className="flex min-h-[560px] flex-col items-center justify-center">
                <Spinner />
              </div>
            ) : data ? (
              <CandidateProfileContent data={data} />
            ) : null}
          </div>
        </div>
      </div>
      {deleteConfirmOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-neutral-950">Remove this application?</h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              This application will be removed from your organization dashboard. This action cannot be undone.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={Boolean(actionId)}
                onClick={() => setDeleteConfirmOpen(false)}
                className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={Boolean(actionId)}
                onClick={removeApplication}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
              >
                {actionId === 'delete' ? 'Removing...' : 'Remove application'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
};

export default OrganizationCandidateApplicationPage;
