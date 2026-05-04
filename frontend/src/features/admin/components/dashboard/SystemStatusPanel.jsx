import { Activity } from 'lucide-react';

import MetricTile from './MetricTile.jsx';
import StatusBadge from './StatusBadge.jsx';
import { formatDateTime, formatNumber, getSystemStatus } from './dashboard.Utils.js';

const SystemStatusPanel = ({ dashboard }) => {
  const system = getSystemStatus(dashboard);
  const activeAlerts = dashboard?.monitoring?.alerts?.length || 0;
  const workers = dashboard?.celery?.workers ?? 0;
  const lastRun = formatDateTime(dashboard?.pipeline?.last_run);

  return (
    <div className="mb-8 rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-4">
          <div className={`rounded-lg p-3 ${system.iconTone}`}>
            <Activity className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-lg font-semibold text-neutral-900">{system.status}</h2>
              <StatusBadge status={dashboard?.pipeline?.status || 'idle'} />
            </div>
            <p className="mt-1 max-w-2xl text-sm text-neutral-600">{system.detail}</p>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[520px]">
          <MetricTile label="Active alerts" value={formatNumber(activeAlerts)} tone={activeAlerts ? 'yellow' : 'green'} />
          <MetricTile label="Workers" value={formatNumber(workers)} tone={workers > 0 ? 'green' : 'yellow'} />
          <MetricTile label="Last run" value={lastRun} />
        </div>
      </div>
    </div>
  );
};

export default SystemStatusPanel;
