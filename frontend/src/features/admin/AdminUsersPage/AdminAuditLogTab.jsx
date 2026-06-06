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

const ACTION_META = {
  SUSPEND: {
    label: 'Suspension',
    icon: UserX,
    className: 'bg-red-50 text-red-700 border-red-200',
  },
  REACTIVATE: {
    label: 'Reactivation',
    icon: UserCheck,
    className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  TOGGLE_ADMIN: {
    label: 'Role change',
    icon: ShieldCheck,
    className: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  TOGGLE_ACTIVE: {
    label: 'Status change',
    icon: UserCog,
    className: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  APPROVE_ORG_OPPORTUNITY: {
    label: 'Opportunity approved',
    icon: CheckCircle2,
    className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  REJECT_ORG_OPPORTUNITY: {
    label: 'Opportunity rejected',
    icon: ShieldX,
    className: 'bg-red-50 text-red-700 border-red-200',
  },
};

const PAGE_SIZE = 25;

const statusLabel = (status) => {
  const value = String(status || '').toUpperCase();
  if (value === 'ACTIVE') return 'Active';
  if (value === 'PENDING_REVIEW') return 'Pending review';
  if (value === 'REJECTED') return 'Rejected';
  if (value === 'ARCHIVEE' || value === 'ARCHIVED') return 'Archived';
  if (value === 'EXPIREE' || value === 'EXPIRED') return 'Expired';
  return status || '-';
};

const decisionLabel = (decision) => {
  const value = String(decision || '').toLowerCase();
  if (value === 'approved') return 'Approved';
  if (value === 'rejected') return 'Rejected';
  if (value === 'pending_review') return 'Pending review';
  return decision || '-';
};

const DetailItem = ({ label, value, wide = false }) => (
  <div className={wide ? 'sm:col-span-2' : ''}>
    <p className="text-xs font-medium uppercase text-neutral-500">{label}</p>
    <p className="mt-1 break-words text-sm text-neutral-900">{value || '-'}</p>
  </div>
);

const AuditDetailModal = ({ entry, onClose }) => {
  if (!entry) return null;

  const metadata = entry.metadata || {};
  const actionMeta = ACTION_META[entry.action] || {
    label: entry.action,
    icon: RotateCcw,
    className: 'bg-neutral-50 text-neutral-700 border-neutral-200',
  };
  const Icon = actionMeta.icon;
  const isOpportunityAction = Boolean(metadata.opportunity_id || metadata.opportunity_title);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/60 px-4 py-6">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-white shadow-xl" role="dialog" aria-modal="true">
        <div className="flex items-start justify-between gap-4 border-b border-neutral-200 p-5">
          <div className="flex min-w-0 items-start gap-3">
            <span className={`mt-0.5 inline-flex rounded-full border p-2 ${actionMeta.className}`}>
              <Icon className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="break-words text-lg font-semibold text-neutral-900">{actionMeta.label}</h3>
              <p className="mt-1 text-sm text-neutral-500">{formatDateTime(entry.created_at)}</p>
            </div>
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close details">
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        <div className="space-y-5 overflow-y-auto p-5 text-sm">
          <section className="rounded-lg border border-neutral-200 p-4">
            <h4 className="text-sm font-semibold text-neutral-900">Action summary</h4>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <DetailItem label="Decision" value={decisionLabel(metadata.decision)} />
              <DetailItem label="Result" value={entry.detail || metadata.message} />
              <DetailItem label="Admin" value={entry.actor_email || 'Unknown admin'} />
              <DetailItem label="Target account" value={entry.target_email || 'Deleted user'} />
              {isOpportunityAction ? (
                <>
                  <DetailItem label="Opportunity ID" value={metadata.opportunity_id ? `#${metadata.opportunity_id}` : '-'} />
                  <DetailItem label="Organization email" value={metadata.organization_email} />
                  <DetailItem label="Opportunity title" value={metadata.opportunity_title} wide />
                </>
              ) : null}
            </div>
          </section>

          {isOpportunityAction ? (
            <section className="rounded-lg border border-neutral-200 p-4">
              <h4 className="text-sm font-semibold text-neutral-900">Organization details</h4>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <DetailItem label="Organization name" value={metadata.organization_name} />
                <DetailItem label="Organization email" value={metadata.organization_email} />
                <DetailItem label="Phone" value={metadata.organization_phone} />
                <DetailItem label="Type" value={metadata.organization_type} />
                <DetailItem label="Contact person" value={metadata.organization_contact_name} />
                <DetailItem label="Website" value={metadata.organization_website} />
              </div>
            </section>
          ) : null}

          {isOpportunityAction ? (
            <section className="rounded-lg border border-neutral-200 p-4">
              <h4 className="text-sm font-semibold text-neutral-900">Publication status</h4>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <DetailItem label="Before" value={statusLabel(metadata.before_status)} />
                <DetailItem label="After" value={statusLabel(metadata.after_status)} />
                <DetailItem label="Admin note" value={metadata.note || 'No note provided'} wide />
              </div>
            </section>
          ) : null}

          <section className="rounded-lg border border-neutral-200 p-4">
            <h4 className="text-sm font-semibold text-neutral-900">Request context</h4>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <DetailItem label="Audit action" value={actionMeta.label} />
              <DetailItem label="Audit ID" value={entry.id ? `#${entry.id}` : '-'} />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

const AdminAuditLogTab = () => {
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
            <CardTitle className="text-base">Audit log</CardTitle>
            <p className="mt-1 text-sm text-neutral-500">
              Immutable chronological trail of sensitive admin actions.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Select value={action || 'all'} onValueChange={handleActionChange}>
              <SelectTrigger className="h-9 w-full border-neutral-200 bg-white sm:w-56">
                <SelectValue placeholder="Filter action" />
              </SelectTrigger>
              <SelectContent>
                {AUDIT_ACTION_OPTIONS.map((option) => (
                  <SelectItem key={option.value || 'all'} value={option.value || 'all'}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="button" variant="outline" size="sm" onClick={exportCsv}>
              <Download className="h-4 w-4" aria-hidden="true" />
              Export CSV
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={exportPdf}>
              <FileText className="h-4 w-4" aria-hidden="true" />
              Export PDF
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
                <TableHead className="px-4 py-3">Action</TableHead>
                <TableHead className="px-4 py-3">User email</TableHead>
                <TableHead className="px-4 py-3">Admin email</TableHead>
                <TableHead className="px-4 py-3">Details</TableHead>
                <TableHead className="px-4 py-3">Date</TableHead>
                <TableHead className="px-4 py-3 text-right">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody aria-busy={isLoading}>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="px-4 py-10 text-center text-neutral-500">
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                      Loading audit log...
                    </span>
                  </TableCell>
                </TableRow>
              ) : logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="px-4 py-10 text-center text-neutral-500">
                    No audit events found.
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((entry) => {
                  const meta = ACTION_META[entry.action] || {
                    label: entry.action,
                    icon: RotateCcw,
                    className: 'bg-neutral-50 text-neutral-700 border-neutral-200',
                  };
                  const Icon = meta.icon;
                  return (
                    <TableRow key={entry.id} className="hover:bg-neutral-50/60">
                      <TableCell className="px-4 py-3">
                        <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${meta.className}`}>
                          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                          {meta.label}
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-sm text-neutral-800">
                        {entry.target_email || 'Deleted user'}
                      </TableCell>
                      <TableCell className="px-4 py-3 text-sm text-neutral-600">
                        {entry.actor_email || 'Unknown admin'}
                      </TableCell>
                      <TableCell className="max-w-[320px] px-4 py-3 text-sm text-neutral-600">
                        <span className="line-clamp-2">{entry.detail || '-'}</span>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-sm text-neutral-600">
                        {formatDateTime(entry.created_at)}
                      </TableCell>
                      <TableCell className="px-4 py-3 text-right">
                        <Button type="button" variant="outline" size="sm" onClick={() => setSelectedEntry(entry)}>
                          <Eye className="h-4 w-4" aria-hidden="true" />
                          View
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
          Page {page} of {totalPages} - {count} events
        </span>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!hasPrevious || isLoading}
            onClick={() => setPage((value) => Math.max(value - 1, 1))}
          >
            Previous
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!hasNext || isLoading}
            onClick={() => setPage((value) => value + 1)}
          >
            Next
          </Button>
        </div>
      </div>

      <AuditDetailModal entry={selectedEntry} onClose={() => setSelectedEntry(null)} />
    </div>
  );
};

export default AdminAuditLogTab;
