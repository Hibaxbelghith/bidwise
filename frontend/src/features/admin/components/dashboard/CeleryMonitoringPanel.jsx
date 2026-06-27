import { Server } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import StatusBadge from './StatusBadge.jsx';
import { formatNumber } from './dashboard.Utils.js';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const getCeleryCurrentIssue = (celery, t) => {
  const status = celery?.status || 'degraded';
  const workers = Number(celery?.workers ?? 0);
  const queueLength = Number(celery?.queue_length ?? 0);
  const activeTasks = Number(celery?.active_tasks ?? 0);

  if (celery?.inspect_error) {
    return t('admin.celeryInspectUnavailable');
  }

  if (workers <= 0) {
    return t('admin.celeryNoWorker');
  }

  if (status === 'running' && activeTasks > 0) {
    return t('admin.celeryWorkersProcessing');
  }

  if (status === 'degraded' && queueLength > 0) {
    return t('admin.celeryQueuedTasks');
  }

  if (status === 'healthy') {
    return t('admin.celeryHealthy');
  }

  return t('admin.celeryReviewWorkerState');
};

const issueTextClasses = {
  healthy: 'text-green-700',
  running: 'text-blue-700',
  degraded: 'text-yellow-800',
  failed: 'text-red-700',
};

const CeleryMonitoringPanel = ({ celery }) => {
  const { t } = useLanguage();
  const status = celery?.status || 'degraded';
  const currentIssue = getCeleryCurrentIssue(celery, t);
  const issueTextClass = issueTextClasses[status] || 'text-neutral-600';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Server className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <div>
            <CardTitle>{t('admin.celeryMonitoring')}</CardTitle>
            <CardDescription>{t('admin.celeryMonitoringHelp')}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-4 sm:col-span-2">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.currentStatus')}</p>
            <div className="mt-3">
              <StatusBadge status={status} />
            </div>
            <p className={`mt-3 text-sm ${issueTextClass}`}>
              <span className="font-medium text-neutral-700">{t('admin.currentIssue')}:</span> {currentIssue}
            </p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.workers')}</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.workers ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.activeTasks')}</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.active_tasks ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.scheduled')}</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.scheduled_tasks ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.queueLength')}</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.queue_length ?? 0)}</p>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-neutral-500">{t('admin.reserved')}</p>
            <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(celery?.reserved_tasks ?? 0)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default CeleryMonitoringPanel;
