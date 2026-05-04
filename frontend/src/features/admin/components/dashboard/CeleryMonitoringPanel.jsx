import { Server } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import StatusBadge from './StatusBadge.jsx';
import { formatNumber } from './dashboard.Utils.js';

const CeleryMonitoringPanel = ({ celery }) => (
  <Card>
    <CardHeader>
      <div className="flex items-center gap-3">
        <Server className="h-5 w-5 text-blue-600" aria-hidden="true" />
        <div>
          <CardTitle>Celery Monitoring</CardTitle>
          <CardDescription>Live worker, active task, and scheduled task counts.</CardDescription>
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <p className="text-xs font-medium uppercase text-neutral-500">Status</p>
          <div className="mt-3">
            <StatusBadge status={celery?.status || 'degraded'} />
          </div>
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

export default CeleryMonitoringPanel;
