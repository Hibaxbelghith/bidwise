import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import StatusBadge from './StatusBadge.jsx';
import { formatDateTime, formatNumber } from './dashboard.Utils.js';

const reasonLabels = {
  no_recent_run: 'No recent run recorded',
  celery_unreachable: 'Celery monitoring unavailable',
  no_workers: 'No active worker detected',
  latest_run_failed: 'Latest run failed',
  latest_run_stale: 'Latest run is stale',
  ingestion_running: 'Ingestion is currently running',
  backlog_detected: 'Backlog detected after ingestion',
  alert_warning: 'An active warning needs review',
  alert_critical: 'A critical monitoring alert is active',
};

const toneClasses = {
  healthy: 'border-green-200 bg-green-50',
  running: 'border-blue-200 bg-blue-50',
  degraded: 'border-yellow-200 bg-yellow-50',
  failed: 'border-red-200 bg-red-50',
};

const issueTextClasses = {
  healthy: 'text-green-700',
  running: 'text-blue-700',
  degraded: 'text-yellow-800',
  failed: 'text-red-700',
};

const getReasonLabel = (reason) => reasonLabels[reason] || 'Pipeline state requires review';

const PipelineHealthPanel = ({ pipeline }) => {
  const status = pipeline?.status || 'healthy';
  const reason = getReasonLabel(pipeline?.status_reason);
  const detail = String(pipeline?.status_detail || '').trim();
  const toneClass = toneClasses[status] || 'border-neutral-200 bg-white';
  const issueTextClass = issueTextClasses[status] || 'text-neutral-600';
  const changeRate = Number(pipeline?.stats?.change_rate || 0);
  const runSuccessRate = Number(pipeline?.stats?.run_success_rate || 0);
  const currentIssue = detail || 'No active issue';

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Health</CardTitle>
        <CardDescription>Live pipeline status, current issue, and output from the last completed run.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className={`rounded-lg border p-4 ${toneClass}`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-neutral-600">Current issue</p>
              <p className="mt-1 text-xl font-bold text-neutral-950">{reason}</p>
              <p className={`mt-1 text-sm ${issueTextClass}`}>{currentIssue}</p>
            </div>
            <StatusBadge status={status} />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Last run processed</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(pipeline?.processed ?? 0)}</p>
            <p className="mt-1 text-xs text-neutral-500">Items scanned in the latest completed run</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Changed records</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">
              {formatNumber((pipeline?.created ?? 0) + (pipeline?.updated ?? 0))}
            </p>
            <p className="mt-1 text-xs text-neutral-500">
              {formatNumber(pipeline?.created ?? 0)} created and {formatNumber(pipeline?.updated ?? 0)} updated
            </p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Change rate</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{changeRate.toFixed(1)}%</p>
            <p className="mt-1 text-xs text-neutral-500">Processed items that changed during the last run</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Last completed run</p>
            <p className="mt-2 text-sm font-semibold text-neutral-900">{formatDateTime(pipeline?.last_run)}</p>
            <p className="mt-1 text-xs text-neutral-500">{runSuccessRate.toFixed(1)}% successful runs recently</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default PipelineHealthPanel;
