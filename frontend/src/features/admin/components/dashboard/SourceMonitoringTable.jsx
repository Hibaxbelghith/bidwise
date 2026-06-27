import StatusBadge from './StatusBadge.jsx';
import { formatDateTime, formatNumber, percentFormatter } from './dashboard.Utils.js';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const SourceMonitoringTable = ({ data }) => {
  const { t } = useLanguage();
  if (!data.length) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-200 p-6 text-sm text-neutral-500">
        {t('admin.noSourceRunHistory')}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200">
      <div className="min-w-[1120px]">
        <div className="grid grid-cols-[1.2fr_0.9fr_0.9fr_0.8fr_0.9fr_1.3fr] bg-neutral-50 px-4 py-3 text-xs font-semibold uppercase text-neutral-500">
          <span>{t('admin.source')}</span>
          <span>{t('admin.status')}</span>
          <span>Created · Updated</span>
          <span>{t('admin.changeRate')}</span>
          <span>{t('admin.lastRun')}</span>
          <span>{t('admin.currentIssue')}</span>
        </div>
        {data.map((source) => {
          const name = source?.source || 'Unknown';
          const changeRate = Number((source?.change_rate ?? source?.success_rate) || 0);
          const runSuccessRate = Number(source?.run_success_rate || 0);
          const failedRuns = Number(source?.failed_runs || 0);
          const created = Number(source?.total_created || 0);
          const updated = Number(source?.total_updated || 0);
          const failedPages = Number(source?.total_failed_pages || 0);
          const avgDuration = Number(source?.avg_duration || 0);
          const status = source?.operational_status || 'degraded';
          const statusDetail = source?.operational_detail || '';
          const currentIssue = String(source?.current_issue_summary || '').trim();
          const currentIssueStatus = source?.current_issue_status || 'healthy';
          return (
            <div
              key={name}
              className="grid grid-cols-[1.2fr_0.9fr_0.9fr_0.8fr_0.9fr_1.3fr] items-center border-t border-neutral-200 px-4 py-3 text-sm"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-neutral-900">{name}</p>
                <p className="mt-1 text-xs text-neutral-500">
                  {t('admin.lastActivity')}: {formatDateTime(source?.last_activity_at)}
                </p>
              </div>

              <div className="min-w-0 space-y-1">
                <StatusBadge status={status} />
                <p className="text-xs text-neutral-500">{statusDetail}</p>
              </div>

              <div className="space-y-1">
                <p className="font-medium text-neutral-900">
                  {formatNumber(created)} created · {formatNumber(updated)} updated
                </p>
                <p className="text-xs text-neutral-500">{t('admin.cumulativeChangedRecords')}</p>
              </div>

              <div className="space-y-1">
                <p className="text-neutral-700">{percentFormatter.format(changeRate)}%</p>
                <p className="text-xs text-neutral-500">{t('admin.shareProcessedChanged')}</p>
                <p className={failedRuns > 0 ? 'text-xs font-medium text-red-700' : failedPages > 0 ? 'text-xs font-medium text-yellow-700' : 'text-xs text-neutral-500'}>
                  {percentFormatter.format(runSuccessRate)}% successful runs
                  {failedPages > 0 ? ` · ${formatNumber(failedPages)} failed pages` : ''}
                </p>
              </div>

              <div className="space-y-1">
                <p className="text-neutral-700">{formatDateTime(source?.last_run)}</p>
                <p className="text-xs text-neutral-500">{t('admin.avgDuration')}: {avgDuration.toFixed(1)}s</p>
              </div>

              <div className="min-w-0">
                {currentIssue ? (
                  <p
                    className={`text-sm ${
                      currentIssueStatus === 'failed'
                        ? 'text-red-700'
                        : 'text-yellow-700'
                    }`}
                    title={currentIssue}
                  >
                    {currentIssue}
                  </p>
                ) : (
                  <p className="text-sm text-neutral-500">{t('admin.noActiveIssue')}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SourceMonitoringTable;
