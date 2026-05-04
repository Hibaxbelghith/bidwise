import { formatDateTime, formatNumber, percentFormatter } from './dashboard.Utils.js';

const SourceMonitoringTable = ({ data }) => {
  if (!data.length) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-200 p-6 text-sm text-neutral-500">
        No source run history yet.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200">
      <div className="min-w-[760px]">
        <div className="grid grid-cols-[1.2fr_0.8fr_0.8fr_0.9fr_1fr] bg-neutral-50 px-4 py-3 text-xs font-semibold uppercase text-neutral-500">
          <span>Source</span>
          <span>Success</span>
          <span>Errors</span>
          <span>Avg duration</span>
          <span>Last run</span>
        </div>
        {data.map((source) => {
          const name = source?.source || 'Unknown';
          const successRate = Number(source?.success_rate || 0);
          const failedRuns = Number(source?.failed_runs || 0);
          return (
            <div
              key={name}
              className="grid grid-cols-[1.2fr_0.8fr_0.8fr_0.9fr_1fr] items-center border-t border-neutral-200 px-4 py-3 text-sm"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-neutral-900">{name}</p>
                {source?.is_running ? <p className="text-xs text-blue-600">Running now</p> : null}
              </div>
              <span className="text-neutral-700">{percentFormatter.format(successRate)}%</span>
              <span className={failedRuns > 0 ? 'font-semibold text-red-700' : 'text-neutral-700'}>
                {formatNumber(failedRuns)}
              </span>
              <span className="text-neutral-700">{Number(source?.avg_duration || 0).toFixed(1)}s</span>
              <span className="text-neutral-600">{formatDateTime(source?.last_run)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SourceMonitoringTable;
