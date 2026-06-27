import { useState } from 'react';
import { CheckCircle2, Download, Eye, FileText, Loader2, RotateCcw, ShieldCheck, ShieldX, UserCheck, UserCog, UserX, X } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../../components/ui/select.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../../components/ui/table.jsx';
import { formatDateTime } from '../components/dashboard/dashboard.Utils.js';
import { AUDIT_ACTION_OPTIONS, useAdminAuditLogs } from '../hooks/useAdminAuditLogs.js';
import { useLanguage } from '../../../i18n/LanguageContext.jsx';

const ACTION_META = {
  SUSPEND: {
    labelKey: 'admin.actionSuspension',
    icon: UserX,
    className: 'bg-red-50 text-red-700 border-red-200',
  },
  REACTIVATE: {
    labelKey: 'admin.actionReactivation',
    icon: UserCheck,
    className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  TOGGLE_ADMIN: {
    labelKey: 'admin.actionRoleChange',
    icon: ShieldCheck,
    className: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  TOGGLE_ACTIVE: {
    labelKey: 'admin.actionStatusChange',
    icon: UserCog,
    className: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  APPROVE_ORG_OPPORTUNITY: {
    labelKey: 'admin.actionOpportunityApproved',
    icon: CheckCircle2,
    className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  REJECT_ORG_OPPORTUNITY: {
    labelKey: 'admin.actionOpportunityRejected',
    icon: ShieldX,
    className: 'bg-red-50 text-red-700 border-red-200',
  },
  UPDATE_ORG_OPPORTUNITY: {
    labelKey: 'admin.actionOpportunityUpdated',
    icon: RotateCcw,
    className: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  SUSPEND_ORG_OPPORTUNITY: {
    labelKey: 'admin.actionOpportunitySuspended',
    icon: RotateCcw,
    className: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  ACTIVATE_ORG_OPPORTUNITY: {
    labelKey: 'admin.actionOpportunityActivated',
    icon: CheckCircle2,
    className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  CLOSE_ORG_OPPORTUNITY: {
    labelKey: 'admin.actionOpportunityClosed',
    icon: ShieldX,
    className: 'bg-red-50 text-red-700 border-red-200',
  },
};

const ACTION_OPTION_KEYS = {
  all: 'admin.allActions',
  SUSPEND: 'admin.suspensions',
  REACTIVATE: 'admin.reactivations',
  TOGGLE_ADMIN: 'admin.roleChanges',
  TOGGLE_ACTIVE: 'admin.activeStatusChanges',
  APPROVE_ORG_OPPORTUNITY: 'admin.opportunityApprovals',
  REJECT_ORG_OPPORTUNITY: 'admin.opportunityRejections',
  UPDATE_ORG_OPPORTUNITY: 'admin.opportunityUpdates',
  SUSPEND_ORG_OPPORTUNITY: 'admin.opportunitySuspensions',
  ACTIVATE_ORG_OPPORTUNITY: 'admin.opportunityActivations',
  CLOSE_ORG_OPPORTUNITY: 'admin.opportunityClosures',
};

const AUDIT_DETAIL_KEYS = {
  'User reactivated; refresh tokens revoked.': 'admin.auditUserReactivated',
  'Admin role changed; refresh tokens revoked.': 'admin.auditAdminRoleChanged',
  'Organization opportunity approved for publication.': 'admin.auditOpportunityApproved',
  'Organization opportunity rejected.': 'admin.auditOpportunityRejected',
  'Organization opportunity updated and re-moderated.': 'admin.auditOpportunityUpdated',
  'Organization opportunity activated.': 'admin.auditOpportunityActivated',
  'Organization opportunity closed.': 'admin.auditOpportunityClosed',
  'Organization opportunity suspended.': 'admin.auditOpportunitySuspended',
};

const PAGE_SIZE = 25;

const actionLabel = (action, t) => {
  const meta = ACTION_META[action];
  return meta?.labelKey ? t(meta.labelKey) : action;
};

const translateAuditDetail = (detail, t) => {
  const key = AUDIT_DETAIL_KEYS[detail];
  return key ? t(key) : detail;
};

const statusLabel = (status, t = null) => {
  const value = String(status || '').toUpperCase();
  if (value === 'ACTIVE') return t ? t('admin.statusActive') : 'Active';
  if (value === 'PENDING_REVIEW') return t ? t('admin.pendingReview') : 'Pending review';
  if (value === 'REJECTED') return t ? t('admin.rejected') : 'Rejected';
  if (value === 'SUSPENDUE') return t ? t('admin.statusSuspended') : 'Suspended';
  if (value === 'FERMEE') return t ? t('admin.actionOpportunityClosed') : 'Closed';
  if (value === 'ARCHIVEE' || value === 'ARCHIVED') return t ? t('admin.archived') : 'Archived';
  if (value === 'EXPIREE' || value === 'EXPIRED') return t ? t('admin.expired') : 'Expired';
  return status || '-';
};

const decisionLabel = (decision, t = null) => {
  const value = String(decision || '').toLowerCase();
  if (value === 'approved') return t ? t('admin.approved') : 'Approved';
  if (value === 'rejected') return t ? t('admin.rejected') : 'Rejected';
  if (value === 'pending_review') return t ? t('admin.pendingReview') : 'Pending review';
  if (value === 'needs_changes') return t ? t('admin.needsChanges') : 'Needs changes';
  return decision || '-';
};

const categoryLabel = (category, t = null) => {
  const labels = {
    legitimate_opportunity: t ? t('admin.legitimateOpportunity') : 'Legitimate opportunity',
    scam: t ? t('admin.scamRisk') : 'Scam',
    mlm_or_pyramid: t ? t('admin.mlmRisk') : 'MLM or pyramid scheme',
    advertisement: t ? t('admin.advertisement') : 'Advertisement',
    inappropriate_content: t ? t('admin.inappropriateContent') : 'Inappropriate content',
    irrelevant: t ? t('admin.irrelevantContent') : 'Irrelevant content',
    unclear: t ? t('admin.unclear') : 'Unclear',
  };
  return labels[String(category || '').toLowerCase()] || category || '-';
};

const confidenceLabel = (confidence) => {
  const value = Number(confidence);
  if (!Number.isFinite(value)) return '-';
  return `${Math.round(Math.min(Math.max(value, 0), 1) * 100)}%`;
};

const DetailItem = ({ label, value, wide = false }) => (
  <div className={wide ? 'sm:col-span-2' : ''}>
    <p className="text-xs font-medium uppercase text-neutral-500">{label}</p>
    <p className="mt-1 break-words text-sm text-neutral-900">{value || '-'}</p>
  </div>
);

const AuditDetailModal = ({ entry, onClose }) => {
  const { t } = useLanguage();
  if (!entry) return null;

  const metadata = entry.metadata || {};
  const actionMeta = ACTION_META[entry.action] || {
    icon: RotateCcw,
    className: 'bg-neutral-50 text-neutral-700 border-neutral-200',
  };
  const actionText = actionLabel(entry.action, t);
  const Icon = actionMeta.icon;
  const isOpportunityAction = Boolean(metadata.opportunity_id || metadata.opportunity_title);
  const hasAiContext = Boolean(
    metadata.ai_category
      || metadata.ai_decision
      || metadata.ai_explanation
      || metadata.ai_confidence !== null && metadata.ai_confidence !== undefined,
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/60 px-4 py-6">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-white shadow-xl" role="dialog" aria-modal="true">
        <div className="flex items-start justify-between gap-4 border-b border-neutral-200 p-5">
          <div className="flex min-w-0 items-start gap-3">
            <span className={`mt-0.5 inline-flex rounded-full border p-2 ${actionMeta.className}`}>
              <Icon className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="break-words text-lg font-semibold text-neutral-900">{actionText}</h3>
              <p className="mt-1 text-sm text-neutral-500">{formatDateTime(entry.created_at)}</p>
            </div>
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label={t('common.close')}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        <div className="space-y-5 overflow-y-auto p-5 text-sm">
          <section className="rounded-lg border border-neutral-200 p-4">
            <h4 className="text-sm font-semibold text-neutral-900">{t('admin.actionSummary')}</h4>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <DetailItem label={t('admin.decision')} value={decisionLabel(metadata.decision, t)} />
              <DetailItem label={t('admin.result')} value={translateAuditDetail(entry.detail || metadata.message, t)} />
              <DetailItem label={t('admin.admin')} value={entry.actor_email || t('admin.unknownAdmin')} />
              <DetailItem label={t('admin.targetAccount')} value={entry.target_email || t('admin.deletedUser')} />
              {isOpportunityAction ? (
                <>
                  <DetailItem label={t('admin.opportunityId')} value={metadata.opportunity_id ? `#${metadata.opportunity_id}` : '-'} />
                  <DetailItem label={t('admin.organizationEmail')} value={metadata.organization_email} />
                  <DetailItem label={t('admin.opportunityTitle')} value={metadata.opportunity_title} wide />
                </>
              ) : null}
            </div>
          </section>

          {isOpportunityAction ? (
            <section className="rounded-lg border border-neutral-200 p-4">
              <h4 className="text-sm font-semibold text-neutral-900">{t('admin.organizationDetails')}</h4>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <DetailItem label={t('admin.organizationName')} value={metadata.organization_name} />
                <DetailItem label={t('admin.organizationEmail')} value={metadata.organization_email} />
                <DetailItem label={t('admin.phone')} value={metadata.organization_phone} />
                <DetailItem label={t('admin.type')} value={metadata.organization_type} />
                <DetailItem label={t('admin.contactPerson')} value={metadata.organization_contact_name} />
                <DetailItem label={t('admin.website')} value={metadata.organization_website} />
              </div>
            </section>
          ) : null}

          {isOpportunityAction ? (
            <section className="rounded-lg border border-neutral-200 p-4">
              <h4 className="text-sm font-semibold text-neutral-900">{t('admin.publicationStatus')}</h4>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <DetailItem label={t('admin.before')} value={statusLabel(metadata.before_status, t)} />
                <DetailItem label={t('admin.after')} value={statusLabel(metadata.after_status, t)} />
                {Array.isArray(metadata.changed_fields) && metadata.changed_fields.length ? (
                  <DetailItem label={t('admin.updatedFields')} value={metadata.changed_fields.join(', ')} wide />
                ) : null}
                <DetailItem label={t('admin.adminNote')} value={metadata.note || t('admin.noNoteProvided')} wide />
              </div>
            </section>
          ) : null}

          {isOpportunityAction && hasAiContext ? (
            <section className="rounded-lg border border-blue-200 bg-blue-50/40 p-4">
              <h4 className="text-sm font-semibold text-neutral-900">{t('admin.aiModerationContext')}</h4>
              <p className="mt-1 text-xs text-neutral-600">
                {t('admin.aiModerationContextHelp')}
              </p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <DetailItem label={t('admin.detectedCategory')} value={categoryLabel(metadata.ai_category, t)} />
                <DetailItem label={t('admin.aiRecommendation')} value={decisionLabel(metadata.ai_decision, t)} />
                <DetailItem label={t('admin.aiConfidence')} value={confidenceLabel(metadata.ai_confidence)} />
                <DetailItem label={t('admin.aiExplanation')} value={metadata.ai_explanation} wide />
              </div>
            </section>
          ) : null}

          <section className="rounded-lg border border-neutral-200 p-4">
            <h4 className="text-sm font-semibold text-neutral-900">{t('admin.requestContext')}</h4>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <DetailItem label={t('admin.auditAction')} value={actionText} />
              <DetailItem label={t('admin.auditId')} value={entry.id ? `#${entry.id}` : '-'} />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

const AdminAuditLogTab = () => {
  const { t } = useLanguage();
  const [action, setAction] = useState('');
  const [page, setPage] = useState(1);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const {
    logs,
    count,
    hasNext,
    hasPrevious,
    isLoading,
    error,
    exportCsv,
    exportPdf,
  } = useAdminAuditLogs({ action, page, pageSize: PAGE_SIZE });

  const totalPages = Math.max(Math.ceil(count / PAGE_SIZE), 1);

  const handleActionChange = (value) => {
    setAction(value === 'all' ? '' : value);
    setPage(1);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-col gap-3 border-b border-neutral-200 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-base">{t('admin.actionHistory')}</CardTitle>
            <p className="mt-1 text-sm text-neutral-500">
              {t('admin.actionHistoryHelp')}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Select value={action || 'all'} onValueChange={handleActionChange}>
              <SelectTrigger className="h-9 w-full border-neutral-200 bg-white sm:w-56">
                <SelectValue placeholder={t('admin.filterAction')} />
              </SelectTrigger>
              <SelectContent>
                {AUDIT_ACTION_OPTIONS.map((option) => (
                  <SelectItem key={option.value || 'all'} value={option.value || 'all'}>
                    {t(ACTION_OPTION_KEYS[option.value || 'all'])}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="button" variant="outline" size="sm" onClick={exportCsv}>
              <Download className="h-4 w-4" aria-hidden="true" />
              {t('admin.exportCsv')}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={exportPdf}>
              <FileText className="h-4 w-4" aria-hidden="true" />
              {t('admin.exportPdf')}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {error ? (
            <div className="m-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}
          <Table>
            <TableHeader>
              <TableRow className="bg-neutral-50">
                <TableHead className="px-4 py-3">{t('admin.actions')}</TableHead>
                <TableHead className="px-4 py-3">{t('admin.userEmail')}</TableHead>
                <TableHead className="px-4 py-3">{t('admin.adminEmail')}</TableHead>
                <TableHead className="px-4 py-3">{t('admin.details')}</TableHead>
                <TableHead className="px-4 py-3">{t('admin.date')}</TableHead>
                <TableHead className="px-4 py-3 text-right">{t('admin.details')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody aria-busy={isLoading}>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="px-4 py-10 text-center text-neutral-500">
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                      {t('admin.loadingAuditLog')}
                    </span>
                  </TableCell>
                </TableRow>
              ) : logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="px-4 py-10 text-center text-neutral-500">
                    {t('admin.noAuditEvents')}
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((entry) => {
                  const meta = ACTION_META[entry.action] || {
                    icon: RotateCcw,
                    className: 'bg-neutral-50 text-neutral-700 border-neutral-200',
                  };
                  const Icon = meta.icon;
                  const actionText = actionLabel(entry.action, t);
                  return (
                    <TableRow key={entry.id} className="hover:bg-neutral-50/60">
                      <TableCell className="px-4 py-3">
                        <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${meta.className}`}>
                          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                          {actionText}
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-sm text-neutral-800">
                        {entry.target_email || t('admin.deletedUser')}
                      </TableCell>
                      <TableCell className="px-4 py-3 text-sm text-neutral-600">
                        {entry.actor_email || t('admin.unknownAdmin')}
                      </TableCell>
                      <TableCell className="max-w-[320px] px-4 py-3 text-sm text-neutral-600">
                        <span className="line-clamp-2">{translateAuditDetail(entry.detail, t) || '-'}</span>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-sm text-neutral-600">
                        {formatDateTime(entry.created_at)}
                      </TableCell>
                      <TableCell className="px-4 py-3 text-right">
                        <Button type="button" variant="outline" size="sm" onClick={() => setSelectedEntry(entry)}>
                          <Eye className="h-4 w-4" aria-hidden="true" />
                          {t('admin.viewDetails')}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between text-sm text-neutral-600">
        <span>
          {t('admin.pageOfEvents', { page, totalPages, count })}
        </span>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!hasPrevious || isLoading}
            onClick={() => setPage((value) => Math.max(value - 1, 1))}
          >
            {t('admin.previous')}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!hasNext || isLoading}
            onClick={() => setPage((value) => value + 1)}
          >
            {t('admin.next')}
          </Button>
        </div>
      </div>

      <AuditDetailModal entry={selectedEntry} onClose={() => setSelectedEntry(null)} />
    </div>
  );
};

export default AdminAuditLogTab;
