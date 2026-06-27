import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import StatusBadge from './StatusBadge.jsx';
import { formatDateTime, formatNumber } from './dashboard.Utils.js';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const reasonKeys = {
  no_recent_run: 'admin.pipelineNoRecentRun',
  celery_unreachable: 'admin.pipelineCeleryUnavailable',
  no_workers: 'admin.pipelineNoWorkers',
  latest_run_failed: 'admin.pipelineLatestRunFailed',
  latest_run_stale: 'admin.pipelineLatestRunStale',
  ingestion_running: 'admin.pipelineIngestionRunning',
  backlog_detected: 'admin.pipelineBacklogDetected',
  alert_warning: 'admin.pipelineAlertWarning',
  alert_critical: 'admin.pipelineAlertCritical',
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

const getReasonLabel = (reason, t) => t(reasonKeys[reason] || 'admin.pipelineRequiresReview');

const PipelineHealthPanel = ({ pipeline }) => {
  const { t } = useLanguage();
  const status = pipeline?.status || 'healthy';
  const reason = getReasonLabel(pipeline?.status_reason, t);
  const detail = String(pipeline?.status_detail || '').trim();
  const toneClass = toneClasses[status] || 'border-neutral-200 bg-white';
  const issueTextClass = issueTextClasses[status] || 'text-neutral-600';
  const changeRate = Number(pipeline?.stats?.change_rate || 0);
  const runSuccessRate = Number(pipeline?.stats?.run_success_rate || 0);
  const currentIssue = detail || t('admin.noActiveIssue');

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('admin.pipelineHealth')}</CardTitle>
        <CardDescription>{t('admin.pipelineHealthHelp')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className={`rounded-lg border p-4 ${toneClass}`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-neutral-600">{t('admin.currentIssue')}</p>
              <p className="mt-1 text-xl font-bold text-neutral-950">{reason}</p>
              <p className={`mt-1 text-sm ${issueTextClass}`}>{currentIssue}</p>
            </div>
            <StatusBadge status={status} />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.lastRunProcessed')}</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(pipeline?.processed ?? 0)}</p>
            <p className="mt-1 text-xs text-neutral-500">{t('admin.lastRunProcessedHelp')}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.changedRecords')}</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">
              {formatNumber((pipeline?.created ?? 0) + (pipeline?.updated ?? 0))}
            </p>
            <p className="mt-1 text-xs text-neutral-500">
              {t('admin.createdAndUpdated', { created: formatNumber(pipeline?.created ?? 0), updated: formatNumber(pipeline?.updated ?? 0) })}
            </p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.changeRate')}</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{changeRate.toFixed(1)}%</p>
            <p className="mt-1 text-xs text-neutral-500">{t('admin.changeRateLastRunHelp')}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.lastCompletedRun')}</p>
            <p className="mt-2 text-sm font-semibold text-neutral-900">{formatDateTime(pipeline?.last_run)}</p>
            <p className="mt-1 text-xs text-neutral-500">{t('admin.successfulRunsRecently', { percent: runSuccessRate.toFixed(1) })}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default PipelineHealthPanel;
