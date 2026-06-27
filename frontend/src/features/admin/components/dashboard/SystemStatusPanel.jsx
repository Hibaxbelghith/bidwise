import { Activity } from 'lucide-react';

import MetricTile from './MetricTile.jsx';
import StatusBadge from './StatusBadge.jsx';
import { formatDateTime, formatNumber, getSystemStatus } from './dashboard.Utils.js';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const SystemStatusPanel = ({ dashboard }) => {
  const { t } = useLanguage();
  const system = getSystemStatus(dashboard);
  const pipelineStatus = dashboard?.pipeline?.status || 'healthy';
  const activeAlerts = dashboard?.monitoring?.alerts?.length || 0;
  const lastCompletedRun = formatDateTime(dashboard?.pipeline?.last_run);
  const currentIssue = dashboard?.pipeline?.status_detail || t('admin.noActiveIssue');
  const detailMatchesCurrentIssue = String(system.detail || '').trim() === String(currentIssue || '').trim();
  const issueTextClass =
    pipelineStatus === 'failed'
      ? 'text-red-700'
      : pipelineStatus === 'degraded'
        ? 'text-yellow-800'
        : pipelineStatus === 'running'
          ? 'text-blue-700'
          : 'text-green-700';

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
              <StatusBadge status={pipelineStatus} />
            </div>
            <p className="mt-1 max-w-2xl text-sm text-neutral-600">{system.detail}</p>
            {!detailMatchesCurrentIssue ? (
              <p className={`mt-2 text-sm ${issueTextClass}`}>
                <span className="font-medium text-neutral-700">{t('admin.currentIssue')}:</span> {currentIssue}
              </p>
            ) : null}
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[360px]">
          <MetricTile label={t('admin.activeAlerts')} value={formatNumber(activeAlerts)} tone={activeAlerts ? 'yellow' : 'green'} />
          <MetricTile label={t('admin.lastCompletedRun')} value={lastCompletedRun} />
        </div>
      </div>
    </div>
  );
};

export default SystemStatusPanel;
