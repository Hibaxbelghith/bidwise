import { Server } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import StatusBadge from './StatusBadge.jsx';
import { formatNumber } from './dashboard.Utils.js';

const getCeleryCurrentIssue = (celery) => {
  const status = celery?.status || 'degraded';
  const workers = Number(celery?.workers ?? 0);
  const queueLength = Number(celery?.queue_length ?? 0);
  const activeTasks = Number(celery?.active_tasks ?? 0);

  if (celery?.inspect_error) {
    return 'Celery inspect is temporarily unavailable, so live worker supervision cannot be fully confirmed.';
  }

  if (workers <= 0) {
    return 'No active Celery worker detected for ingestion tasks.';
  }

  if (status === 'running' && activeTasks > 0) {
    return 'Workers are actively processing pipeline tasks.';
  }

  if (status === 'degraded' && queueLength > 0) {
    return 'Tasks are queued and should be watched until workers fully drain the backlog.';
  }

  if (status === 'healthy') {
    return 'No active issue. Worker availability and queue activity are within expected ranges.';
  }

  return 'Worker state should be reviewed.';
};

const issueTextClasses = {
  healthy: 'text-green-700',
  running: 'text-blue-700',
  degraded: 'text-yellow-800',
  failed: 'text-red-700',
};

const CeleryMonitoringPanel = ({ celery }) => {
  const status = celery?.status || 'degraded';
  const currentIssue = getCeleryCurrentIssue(celery);
  const issueTextClass = issueTextClasses[status] || 'text-neutral-600';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Server className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <div>
            <CardTitle>Celery Monitoring</CardTitle>
            <CardDescription>Live worker status and queue activity for the current pipeline runtime.</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-4 sm:col-span-2">
            <p className="text-xs font-medium uppercase text-neutral-500">Current status</p>
            <div className="mt-3">
              <StatusBadge status={status} />
            </div>
            <p className={`mt-3 text-sm ${issueTextClass}`}>
              <span className="font-medium text-neutral-700">Current issue:</span> {currentIssue}
            </p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Workers</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.workers ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Active tasks</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.active_tasks ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Scheduled</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.scheduled_tasks ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Queue length</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.queue_length ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">Reserved</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.reserved_tasks ?? 0)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default CeleryMonitoringPanel;
