import { useCallback, useEffect, useMemo, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const PIPELINE_METRICS_URL = `${API_BASE_URL.replace(/\/$/, '')}/metrics/pipeline/`;
const AUTO_REFRESH_MS = 30000;

const cardClassName = 'rounded-lg border border-neutral-200 bg-white p-4';

const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(2)}%`;

const getPipelineInterpretation = ({ successRate, rejectionRate, backlogRate }) => {
  if (successRate >= 0.85 && rejectionRate <= 0.15 && backlogRate <= 0.25) {
    return {
      label: 'Healthy',
      message: 'High conversion, low rejection, and controlled backlog.',
      toneClass: 'border-green-200 bg-green-50 text-green-800',
      dotClass: 'bg-green-600',
    };
  }

  if (successRate >= 0.6 && rejectionRate <= 0.35 && backlogRate <= 0.5) {
    return {
      label: 'Needs Attention',
      message: 'Pipeline is stable but some quality or backlog issues need monitoring.',
      toneClass: 'border-amber-200 bg-amber-50 text-amber-800',
      dotClass: 'bg-amber-500',
    };
  }

  return {
    label: 'Critical',
    message: 'Rejection or backlog is too high and requires immediate action.',
    toneClass: 'border-red-200 bg-red-50 text-red-800',
    dotClass: 'bg-red-600',
  };
};

export default function PipelineMetrics() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadMetrics = useCallback(async ({ silent = false } = {}) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError('');

    try {
      const response = await fetch(PIPELINE_METRICS_URL, {
        headers: {
          Accept: 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to load metrics (${response.status})`);
      }

      const data = await response.json();
      setMetrics(data);
      setLastUpdated(new Date());
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Unable to load metrics');
    } finally {
      if (silent) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let active = true;
    loadMetrics();

    const intervalId = setInterval(() => {
      if (active) {
        loadMetrics({ silent: true });
      }
    }, AUTO_REFRESH_MS);

    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, [loadMetrics]);

  const display = useMemo(() => {
    const safeMetrics = metrics || {};
    const totalRaw = Number(safeMetrics.total_raw || 0);
    const materialized = Number(safeMetrics.materialized_count || 0);
    const rejected = Number(safeMetrics.rejected_count || 0);
    const newCount = Number(safeMetrics.new_count || Math.max(totalRaw - materialized - rejected, 0));
    const processedCount = Number(safeMetrics.processed_count || materialized + rejected);

    const successRate = Number(
      safeMetrics.success_rate ??
        safeMetrics.processing_success_rate ??
        (processedCount ? materialized / processedCount : 0)
    );
    const rejectionRate = Number(
      safeMetrics.rejection_rate ?? (processedCount ? rejected / processedCount : 0)
    );
    const backlogRate = Number(
      safeMetrics.backlog_rate ?? (totalRaw ? newCount / totalRaw : 0)
    );
    const overallSuccessRate = Number(
      safeMetrics.overall_success_rate ?? (totalRaw ? materialized / totalRaw : 0)
    );

    return {
      totalRaw,
      materialized,
      rejected,
      newCount,
      processedCount,
      successRate,
      rejectionRate,
      backlogRate,
      overallSuccessRate,
      materializedShare: totalRaw ? materialized / totalRaw : 0,
      rejectedShare: totalRaw ? rejected / totalRaw : 0,
      newShare: totalRaw ? newCount / totalRaw : 0,
    };
  }, [metrics]);

  const interpretation = useMemo(() => getPipelineInterpretation(display), [display]);

  return (
    <section className="mb-8" aria-labelledby="pipeline-metrics-heading">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="pipeline-metrics-heading" className="text-xl font-semibold text-neutral-900">
            Pipeline Metrics
          </h2>
          <p className="text-sm text-neutral-600">Operational view of raw processing status</p>
        </div>

        <div className="flex items-center gap-3 text-xs text-neutral-600">
          <span>
            Auto refresh: {Math.round(AUTO_REFRESH_MS / 1000)}s
            {refreshing ? ' (updating...)' : ''}
          </span>
          {lastUpdated && <span>Last update: {lastUpdated.toLocaleTimeString()}</span>}
          <button
            type="button"
            onClick={() => loadMetrics({ silent: true })}
            className="rounded border border-neutral-300 px-2 py-1 text-neutral-700 hover:bg-neutral-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {loading && (
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-neutral-600">
          Loading pipeline metrics...
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-4">
          <div className={`rounded-lg border p-4 ${interpretation.toneClass}`}>
            <div className="flex items-center gap-2">
              <span className={`inline-block h-2.5 w-2.5 rounded-full ${interpretation.dotClass}`} aria-hidden="true" />
              <p className="text-sm font-semibold">Interpretation: {interpretation.label}</p>
            </div>
            <p className="mt-1 text-sm">{interpretation.message}</p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div className={cardClassName}>
              <p className="text-sm text-neutral-600">Total Raw</p>
              <p className="mt-1 text-2xl font-bold text-neutral-900">{display.totalRaw}</p>
              <p className="mt-1 text-xs text-neutral-500">Processed: {display.processedCount}</p>
            </div>

            <div className={cardClassName}>
              <p className="text-sm text-neutral-600">Materialized</p>
              <p className="mt-1 text-2xl font-bold text-green-700">{display.materialized}</p>
              <p className="mt-1 text-xs text-neutral-500">{formatPercent(display.materializedShare)} of total</p>
            </div>

            <div className={cardClassName}>
              <p className="text-sm text-neutral-600">Rejected</p>
              <p className="mt-1 text-2xl font-bold text-red-700">{display.rejected}</p>
              <p className="mt-1 text-xs text-neutral-500">{formatPercent(display.rejectedShare)} of total</p>
            </div>

            <div className={cardClassName}>
              <p className="text-sm text-neutral-600">Success Rate</p>
              <p className="mt-1 text-2xl font-bold text-neutral-900">{formatPercent(display.successRate)}</p>
              <p className="mt-1 text-xs text-neutral-500">Global: {formatPercent(display.overallSuccessRate)}</p>
            </div>

            <div className={cardClassName}>
              <p className="text-sm text-neutral-600">Backlog Rate</p>
              <p className="mt-1 text-2xl font-bold text-neutral-900">{formatPercent(display.backlogRate)}</p>
              <p className="mt-1 text-xs text-neutral-500">Rejection: {formatPercent(display.rejectionRate)}</p>
            </div>
          </div>

          <div className="rounded-lg border border-neutral-200 bg-white p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium text-neutral-700">Pipeline distribution</p>
              <p className="text-xs text-neutral-500">materialized / rejected / new</p>
            </div>

            <div className="flex h-3 overflow-hidden rounded-full bg-neutral-200" role="img" aria-label="Pipeline distribution bar">
              <div
                className="h-full bg-green-500"
                style={{ width: `${(display.materializedShare * 100).toFixed(2)}%` }}
              />
              <div
                className="h-full bg-red-500"
                style={{ width: `${(display.rejectedShare * 100).toFixed(2)}%` }}
              />
              <div
                className="h-full bg-amber-400"
                style={{ width: `${(display.newShare * 100).toFixed(2)}%` }}
              />
            </div>

            <div className="mt-3 grid gap-2 text-xs text-neutral-700 sm:grid-cols-3">
              <div className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
                <span>Materialized: {formatPercent(display.materializedShare)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-red-500" aria-hidden="true" />
                <span>Rejected: {formatPercent(display.rejectedShare)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-amber-400" aria-hidden="true" />
                <span>New: {formatPercent(display.newShare)}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
