import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Mail, Trash2, X } from 'lucide-react';

import { useLanguage } from '../../../i18n/LanguageContext.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../../components/ui/table.jsx';
import { getApplicationStatusMeta } from '../../applications/applicationStatusUi.js';
import { acceptApplication, deleteApplication, rejectApplication } from '../services/organizationService.js';

const PAGE_SIZE = 10;

const formatDate = (dateString, language = 'en') => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-GB', options);
  } catch {
    return '';
  }
};

const getTimeAgo = (dateString, t, language) => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return t('organization.justNow');
    if (seconds < 3600) return t('organization.minutesAgoShort', { count: Math.floor(seconds / 60) });
    if (seconds < 86400) return t('organization.hoursAgoShort', { count: Math.floor(seconds / 3600) });
    if (seconds < 604800) return t('organization.daysAgoShort', { count: Math.floor(seconds / 86400) });
    return formatDate(dateString, language);
  } catch {
    return '';
  }
};

const getActivityLines = (application, t, language) => {
  const status = String(application?.statut || '').trim();
  const submittedAt = application?.submitted_at;
  const updatedAt = application?.derniere_mise_a_jour;
  const appliedLabel = getTimeAgo(submittedAt, t, language);
  const actionLabel = getTimeAgo(updatedAt, t, language);
  const hasActionTimestamp =
    submittedAt &&
    updatedAt &&
    Math.abs(new Date(updatedAt).getTime() - new Date(submittedAt).getTime()) > 1000;
  const withTime = (key, value) => (value ? t(key, { time: value }) : t(key));

  if (status === 'SUBMITTED') {
    return [withTime('organization.activityApplied', appliedLabel)];
  }
  if (status === 'VIEWED_BY_ORGANIZATION') {
    return hasActionTimestamp
      ? [
          withTime('organization.activityApplied', appliedLabel),
          withTime('organization.activityUnderReview', actionLabel),
        ]
      : [withTime('organization.activityApplied', appliedLabel)];
  }
  if (status === 'SHORTLISTED') {
    return hasActionTimestamp
      ? [
          withTime('organization.activityApplied', appliedLabel),
          withTime('organization.activityPreselected', actionLabel),
        ]
      : [withTime('organization.activityApplied', appliedLabel)];
  }
  if (status === 'REJECTED') {
    return hasActionTimestamp
      ? [
          withTime('organization.activityApplied', appliedLabel),
          withTime('organization.activityRejected', actionLabel),
        ]
      : [withTime('organization.activityApplied', appliedLabel)];
  }
  if (status === 'WITHDRAWN') {
    return hasActionTimestamp
      ? [
          withTime('organization.activityApplied', appliedLabel),
          withTime('organization.activityWithdrawn', actionLabel),
        ]
      : [withTime('organization.activityApplied', appliedLabel)];
  }
  return [withTime('organization.activityApplied', appliedLabel)];
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

const OrganizationApplicationsTable = ({ applications, onStatusChange }) => {
  const { language, t } = useLanguage();
  const [page, setPage] = useState(1);
  const [reviewingId, setReviewingId] = useState(null);
  const [rejectingId, setRejectingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [actionError, setActionError] = useState('');
  const [selectedAction, setSelectedAction] = useState(null); // { appId, type: 'review' | 'reject' }
  const totalPages = Math.max(Math.ceil(applications.length / PAGE_SIZE), 1);
  
  const visibleApplications = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return applications.slice(start, start + PAGE_SIZE);
  }, [applications, page]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const handleReview = async (opportunityId, applicationId, currentStatus, restoreStatus) => {
    setSelectedAction({ appId: applicationId, type: 'review' });
    setReviewingId(applicationId);
    setActionError('');
    try {
      const shouldRestore =
        currentStatus === 'SHORTLISTED' &&
        (restoreStatus === 'SUBMITTED' || restoreStatus === 'VIEWED_BY_ORGANIZATION');
      const result = await acceptApplication(opportunityId, applicationId, {
        restoreStatus: shouldRestore ? restoreStatus : undefined,
      });
      onStatusChange(applicationId, result?.status || 'SHORTLISTED');
      setSelectedAction(null);
    } catch (error) {
      setActionError(error?.response?.data?.detail || t('organization.unableUpdateApplication'));
      setSelectedAction(null);
    } finally {
      setReviewingId(null);
    }
  };

  const handleReject = async (opportunityId, applicationId, currentStatus, restoreStatus) => {
    setSelectedAction({ appId: applicationId, type: 'reject' });
    setRejectingId(applicationId);
    setActionError('');
    try {
      const shouldRestore =
        currentStatus === 'REJECTED' &&
        (restoreStatus === 'SUBMITTED' || restoreStatus === 'VIEWED_BY_ORGANIZATION');
      const result = await rejectApplication(opportunityId, applicationId, {
        restoreStatus: shouldRestore ? restoreStatus : undefined,
      });
      onStatusChange(applicationId, result?.status || 'REJECTED');
      setSelectedAction(null);
    } catch (error) {
      setActionError(error?.response?.data?.detail || t('organization.unableRejectApplication'));
      setSelectedAction(null);
    } finally {
      setRejectingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;

    setDeletingId(deleteConfirm.applicationId);
    setActionError('');
    try {
      await deleteApplication(deleteConfirm.opportunityId, deleteConfirm.applicationId);
      onStatusChange(deleteConfirm.applicationId, '__DELETE__');
      setDeleteConfirm(null);
    } catch (error) {
      setActionError(error?.response?.data?.detail || t('organization.unableDeleteApplication'));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-200 bg-white">
      {deleteConfirm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-neutral-950">{t('organization.deleteApplicationQuestion')}</h3>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              {t('organization.deleteApplicationWarningPrefix')} <span className="font-semibold">{deleteConfirm.candidateName}</span> {t('organization.deleteApplicationWarningSuffix')}
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={Boolean(deletingId)}
                onClick={() => setDeleteConfirm(null)}
                className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
              >
                {t('common.cancel')}
              </button>
              <button
                type="button"
                disabled={Boolean(deletingId)}
                onClick={handleDelete}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deletingId ? t('organization.deleting') : t('organization.deleteApplication')}
              </button>
            </div>
          </div>
        </div>
      ) : null}
      {actionError ? (
        <div className="border-b border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {actionError}
        </div>
      ) : null}
      <Table>
        <TableHeader>
          <TableRow className="bg-neutral-50">
            <TableHead className="w-[40%] px-4">{t('organization.candidate')}</TableHead>
            <TableHead className="w-[35%]">{t('organization.activity')}</TableHead>
            <TableHead className="w-[25%] text-center">{t('organization.interest')}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {visibleApplications.map((application) => {
            const statusBadge = getApplicationStatusMeta(application.statut, 'organization', t);
            const canAct = application.statut !== 'WITHDRAWN';
            const isActionBusy = reviewingId === application.id || rejectingId === application.id || deletingId === application.id;
            const canRestoreToNormal =
              application._restore_status === 'SUBMITTED' ||
              application._restore_status === 'VIEWED_BY_ORGANIZATION';
            const contactMailto = buildContactMailto({
              email: application.contact_email || application.candidate_email,
              candidateName: application.candidate_name,
              opportunityTitle: application.opportunity_title,
            });
            
            return (
              <TableRow key={application.id} className="hover:bg-neutral-50">
                {/* Candidate Column */}
                <TableCell className="px-4">
                  <Link
                    to={`/organization/applications/${application.id}`}
                    className="block space-y-1 hover:opacity-75 transition-opacity"
                  >
                    <div className="font-semibold text-blue-600 hover:text-blue-700">
                      {application.candidate_name}
                    </div>
                    <p className="text-sm text-neutral-600">{application.candidate_email}</p>
                    {application.contact_phone && (
                      <p className="text-sm text-neutral-600">{application.contact_phone}</p>
                    )}
                    <div className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                      {t('organization.appliedTo')}: {application.opportunity_title}
                    </div>
                  </Link>
                </TableCell>

                {/* Activity Column */}
                <TableCell>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className={`inline-block px-2.5 py-0.5 text-xs font-medium rounded ${statusBadge.bgColor} ${statusBadge.textColor}`}>
                        {statusBadge.label}
                      </span>
                    </div>
                    <div className="space-y-1">
                      {getActivityLines(application, t, language).map((line) => (
                        <p key={line} className="text-xs text-neutral-500">
                          {line}
                        </p>
                      ))}
                    </div>
                  </div>
                </TableCell>

                {/* Interest Actions Column */}
                <TableCell className="text-center">
                  <div className="flex items-center justify-center gap-2">
                    {contactMailto ? (
                      <a
                        href={contactMailto}
                        title={t('organization.contactCandidate')}
                        className="inline-flex items-center justify-center w-10 h-10 rounded-lg border border-neutral-300 bg-white text-neutral-900 hover:bg-neutral-100 transition-colors"
                      >
                        <Mail className="h-4 w-4" />
                      </a>
                    ) : null}
                    {canAct && (
                      <div className="inline-flex rounded-lg border border-neutral-300 overflow-hidden bg-white">
                        <button
                          title={
                            application.statut === 'SHORTLISTED' && canRestoreToNormal
                              ? t('organization.undoPreselection')
                              : t('organization.preselectCandidate')
                          }
                          disabled={isActionBusy}
                          onClick={() =>
                            handleReview(
                              application.opportunity_id,
                              application.id,
                              application.statut,
                              application._restore_status
                            )
                          }
                          className={`flex items-center justify-center w-10 h-10 text-neutral-900 transition-colors border-r border-neutral-300 cursor-pointer disabled:opacity-50 ${
                            application.statut === 'SHORTLISTED'
                              ? 'bg-green-100 hover:bg-green-150'
                              : 'hover:bg-neutral-100'
                          }`}
                        >
                          <Check className="h-5 w-5" />
                        </button>
                        <button
                          title={
                            application.statut === 'REJECTED' && canRestoreToNormal
                              ? t('organization.undoRejection')
                              : t('organization.reject')
                          }
                          disabled={isActionBusy}
                          onClick={() =>
                            handleReject(
                              application.opportunity_id,
                              application.id,
                              application.statut,
                              application._restore_status
                            )
                          }
                          className={`flex items-center justify-center w-10 h-10 text-neutral-900 transition-colors border-r border-neutral-300 cursor-pointer disabled:opacity-50 ${
                            application.statut === 'REJECTED'
                              ? 'bg-red-100 hover:bg-red-150'
                              : 'hover:bg-neutral-100'
                          }`}
                        >
                          <X className="h-5 w-5" />
                        </button>
                        <button
                          title={t('organization.delete')}
                          disabled={isActionBusy}
                          onClick={() => setDeleteConfirm({
                            applicationId: application.id,
                            opportunityId: application.opportunity_id,
                            candidateName: application.candidate_name,
                          })}
                          className="flex items-center justify-center w-10 h-10 text-neutral-900 hover:bg-neutral-100 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Trash2 className="h-5 w-5" />
                        </button>
                      </div>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <div className="text-sm text-neutral-600">
            {t('organization.pageOf', { page, totalPages })}
          </div>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => Math.max(p - 1, 1))}
              className="px-3 py-1 text-sm rounded border border-neutral-200 hover:bg-neutral-50 disabled:opacity-50"
            >
              {t('admin.previous')}
            </button>
            <button
              disabled={page === totalPages}
              onClick={() => setPage(p => Math.min(p + 1, totalPages))}
              className="px-3 py-1 text-sm rounded border border-neutral-200 hover:bg-neutral-50 disabled:opacity-50"
            >
              {t('admin.next')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default OrganizationApplicationsTable;
