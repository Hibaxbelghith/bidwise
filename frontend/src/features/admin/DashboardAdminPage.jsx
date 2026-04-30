import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BellRing,
  CheckCircle2,
  Clock3,
  Cpu,
  Database,
  RadioTower,
  Server,
  ShieldCheck,
} from 'lucide-react';

import { Badge } from '../../components/ui/badge.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card.jsx';
import adminApi from '../../lib/adminApi.js';

const numberFormatter = new Intl.NumberFormat('en-US');
const percentFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
});

const emptyDashboard = {
  kpis: {
    total_opportunities: 0,
    pipeline_activity_today: 0,
    sources_count: 0,
    success_rate: 0,
  },
  pipeline: {
    last_run: null,
    status: 'idle',
    processed: 0,
    created: 0,
    updated: 0,
  },
  sources: [],
  celery: {
    workers: 0,
    active_tasks: 0,
    scheduled_tasks: 0,
    reserved_tasks: 0,
    queue_length: 0,
    status: 'degraded',
  },
  monitoring: {
    embeddings: {
      total: 0,
      with_embeddings: 0,
      with_pg_embeddings: 0,
      missing_embeddings: 0,
      coverage: 0,
      is_complete: false,
    },
    pipeline_lag: {
      new_raw_remaining: 0,
      raw_total: 0,
      raw_status_counts: {},
      backlog_detected: false,
    },
    alerts: [],
    sources: [],
    queue: {},
  },
};

const statusStyles = {
  success: 'border-green-200 bg-green-50 text-green-700',
  failed: 'border-red-200 bg-red-50 text-red-700',
  skipped: 'border-yellow-200 bg-yellow-50 text-yellow-700',
  running: 'border-blue-200 bg-blue-50 text-blue-700',
  idle: 'border-neutral-200 bg-neutral-50 text-neutral-700',
  healthy: 'border-green-200 bg-green-50 text-green-700',
  degraded: 'border-yellow-200 bg-yellow-50 text-yellow-700',
};

const formatNumber = (value) => numberFormatter.format(Number(value || 0));

const formatDateTime = (value) => {
  if (!value) return '-';
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

const getSystemStatus = (dashboard) => {
  const activeAlerts = dashboard?.monitoring?.alerts?.length || 0;
  const hasBacklog = Boolean(dashboard?.monitoring?.pipeline_lag?.backlog_detected);
  const workerStatus = dashboard?.celery?.status || 'degraded';
  const pipelineStatus = dashboard?.pipeline?.status || 'idle';

  if (activeAlerts > 0 || hasBacklog || workerStatus === 'degraded' || pipelineStatus === 'failed') {
    return {
      status: 'Attention needed',
      detail: 'Monitoring detected one or more items that need review.',
      iconTone: 'text-yellow-700 bg-yellow-100',
    };
  }

  if (pipelineStatus === 'running') {
    return {
      status: 'Pipeline running',
      detail: 'Ingestion is active and workers are available.',
      iconTone: 'text-blue-700 bg-blue-100',
    };
  }

  return {
    status: 'Healthy',
    detail: 'Sources, workers, and freshness checks are within expected ranges.',
    iconTone: 'text-green-700 bg-green-100',
  };
};

const KpiCard = ({ title, value, icon: Icon }) => (
  <Card>
    <CardHeader className="pb-3">
      <CardTitle className="text-sm font-medium text-neutral-600">{title}</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="flex items-center justify-between gap-4">
        <p className="text-3xl font-bold text-neutral-900">{value}</p>
        <Icon className="h-8 w-8 text-blue-600" aria-hidden="true" />
      </div>
    </CardContent>
  </Card>
);

const MetricTile = ({ label, value, detail, tone = 'neutral' }) => {
  const toneClasses = {
    blue: 'border-blue-200 bg-blue-50 text-blue-800',
    green: 'border-green-200 bg-green-50 text-green-800',
    yellow: 'border-yellow-200 bg-yellow-50 text-yellow-800',
    red: 'border-red-200 bg-red-50 text-red-800',
    neutral: 'border-neutral-200 bg-white text-neutral-900',
  };

  return (
    <div className={`rounded-lg border p-4 ${toneClasses[tone] || toneClasses.neutral}`}>
      <p className="text-xs font-medium uppercase opacity-75">{label}</p>
      <p className="mt-2 text-xl font-bold">{value}</p>
      {detail ? <p className="mt-1 text-xs opacity-75">{detail}</p> : null}
    </div>
  );
};

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

const EmptyChart = () => (
  <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-neutral-200 text-sm text-neutral-500">
    No data available
  </div>
);

const SourceBarChart = ({ data }) => {
  const maxCount = Math.max(...data.map((item) => item.count), 0);

  if (!data.length || maxCount === 0) return <EmptyChart />;

  return (
    <div className="space-y-4">
      {data.map((item) => {
        const width = `${Math.max((item.count / maxCount) * 100, 3)}%`;
        return (
          <div key={item.name} className="space-y-2">
            <div className="flex items-center justify-between gap-4 text-sm">
              <span className="truncate font-medium text-neutral-700">{item.name}</span>
              <span className="text-neutral-500">{formatNumber(item.count)}</span>
            </div>
            <div className="h-3 rounded-full bg-neutral-100">
              <div className="h-3 rounded-full bg-blue-600" style={{ width }} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

const StatusBadge = ({ status }) => (
  <Badge variant="outline" className={statusStyles[status] || 'border-neutral-200 text-neutral-700'}>
    {status}
  </Badge>
);

const severityStyles = {
  INFO: 'border-blue-200 bg-blue-50 text-blue-700',
  WARNING: 'border-yellow-200 bg-yellow-50 text-yellow-800',
  CRITICAL: 'border-red-200 bg-red-50 text-red-700',
};

const AlertList = ({ alerts }) => {
  if (!alerts.length) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-800">
        No active pipeline alerts.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div key={alert.issue_key} className="rounded-lg border border-neutral-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="outline" className={severityStyles[alert.severity] || severityStyles.INFO}>
              {alert.severity}
            </Badge>
            {alert.source ? <span className="text-sm font-semibold text-neutral-900">{alert.source}</span> : null}
          </div>
          <p className="mt-2 font-medium text-neutral-900">{alert.title}</p>
          {alert.details ? <p className="mt-1 text-sm text-neutral-600">{alert.details}</p> : null}
        </div>
      ))}
    </div>
  );
};

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

const DashboardAdminPage = () => {
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadDashboard = async () => {
      try {
        setIsLoading(true);
        setError('');
        const { data } = await adminApi.get('/admin/dashboard/');
        if (isMounted) {
          setDashboard({
            ...emptyDashboard,
            ...data,
            kpis: { ...emptyDashboard.kpis, ...(data?.kpis || {}) },
            pipeline: { ...emptyDashboard.pipeline, ...(data?.pipeline || {}) },
            celery: { ...emptyDashboard.celery, ...(data?.celery || {}) },
            sources: Array.isArray(data?.sources) ? data.sources : [],
            monitoring: {
              ...emptyDashboard.monitoring,
              ...(data?.monitoring || {}),
              embeddings: {
                ...emptyDashboard.monitoring.embeddings,
                ...(data?.monitoring?.embeddings || {}),
              },
              pipeline_lag: {
                ...emptyDashboard.monitoring.pipeline_lag,
                ...(data?.monitoring?.pipeline_lag || {}),
              },
              sources: Array.isArray(data?.monitoring?.sources) ? data.monitoring.sources : [],
              alerts: Array.isArray(data?.monitoring?.alerts) ? data.monitoring.alerts : [],
            },
          });
        }
      } catch (requestError) {
        if (isMounted) {
          setError(requestError.response?.data?.detail || 'Unable to load admin dashboard.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadDashboard();

    return () => {
      isMounted = false;
    };
  }, []);

  const kpis = useMemo(
    () => [
      {
        title: 'Total Opportunities',
        value: formatNumber(dashboard?.kpis?.total_opportunities ?? 0),
        icon: Database,
      },
      {
        title: 'Pipeline Activity Today',
        value: formatNumber(dashboard?.kpis?.pipeline_activity_today ?? 0),
        icon: Clock3,
      },
      {
        title: 'Active Sources',
        value: formatNumber(dashboard?.kpis?.sources_count ?? 0),
        icon: RadioTower,
      },
      {
        title: 'Success Rate',
        value: `${percentFormatter.format(Number(dashboard?.kpis?.success_rate ?? 0))}%`,
        icon: CheckCircle2,
      },
    ],
    [dashboard]
  );
  const embeddings = dashboard?.monitoring?.embeddings || emptyDashboard.monitoring.embeddings;
  const pipelineLag = dashboard?.monitoring?.pipeline_lag || emptyDashboard.monitoring.pipeline_lag;
  const monitoringSources = dashboard?.monitoring?.sources || [];
  const monitoringAlerts = dashboard?.monitoring?.alerts || [];

  if (isLoading) {
    return (
      <section className="bg-neutral-50" aria-labelledby="admin-dashboard-heading">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="mb-8">
            <div className="mb-3 h-9 w-72 animate-pulse rounded-md bg-neutral-200" />
            <div className="h-5 w-96 max-w-full animate-pulse rounded-md bg-neutral-200" />
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((item) => (
              <Card key={item}>
                <CardContent className="p-6">
                  <div className="h-20 animate-pulse rounded-md bg-neutral-100" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="bg-neutral-50" aria-labelledby="admin-dashboard-heading">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <h1 id="admin-dashboard-heading" className="text-3xl font-bold text-neutral-900">
              Admin Panel
            </h1>
            <Badge variant="secondary" className="gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Monitoring
            </Badge>
            {dashboard?.celery?.status === 'degraded' ? (
              <Badge variant="outline" className="border-yellow-200 bg-yellow-50 text-yellow-700">
                Worker unavailable
              </Badge>
            ) : null}
          </div>
          <p className="text-neutral-600">Operational monitoring for opportunity ingestion, source freshness, workers, and alerts.</p>
        </div>

        <SystemStatusPanel dashboard={dashboard} />

        {error ? (
          <Card className="mb-8 border-red-200 bg-red-50">
            <CardContent className="p-6">
              <p className="font-medium text-red-800">{error}</p>
            </CardContent>
          </Card>
        ) : null}

        <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4" role="region" aria-label="Admin dashboard statistics">
          {kpis.map((kpi) => (
            <KpiCard key={kpi.title} {...kpi} />
          ))}
        </div>

        <div className="mb-8 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Cpu className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>AI Readiness</CardTitle>
                  <CardDescription>Embedding coverage required by match score and similar opportunities.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-3">
              <MetricTile
                label="Coverage"
                value={`${percentFormatter.format(Number(embeddings.coverage || 0))}%`}
                detail={`${formatNumber(embeddings.with_embeddings)} / ${formatNumber(embeddings.total)}`}
                tone={embeddings.is_complete ? 'green' : 'yellow'}
              />
              <MetricTile
                label="Missing"
                value={formatNumber(embeddings.missing_embeddings)}
                detail="Opportunities without vectors"
                tone={Number(embeddings.missing_embeddings || 0) > 0 ? 'yellow' : 'green'}
              />
              <MetricTile
                label="pgvector"
                value={formatNumber(embeddings.with_pg_embeddings)}
                detail="Indexed vector payloads"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>Pipeline Lag</CardTitle>
                  <CardDescription>Raw backlog that must reach zero after a complete run.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <MetricTile
                label="NEW raw"
                value={formatNumber(pipelineLag.new_raw_remaining)}
                detail={pipelineLag.backlog_detected ? 'Backlog detected' : 'No backlog'}
                tone={pipelineLag.backlog_detected ? 'red' : 'green'}
              />
              <MetricTile
                label="Raw total"
                value={formatNumber(pipelineLag.raw_total)}
                detail="All raw records"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <BellRing className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>Active Alerts</CardTitle>
                  <CardDescription>Automatic anomaly detection for source freshness and pipeline health.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <AlertList alerts={monitoringAlerts} />
            </CardContent>
          </Card>
        </div>

        <div className="mb-8 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Opportunities by Source</CardTitle>
              <CardDescription>Current materialized opportunity volume by source.</CardDescription>
            </CardHeader>
            <CardContent>
              <SourceBarChart data={dashboard?.sources || []} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Pipeline Health</CardTitle>
              <CardDescription>Current pipeline and Celery worker state.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-4">
                <div>
                  <p className="text-sm font-medium text-neutral-600">Pipeline status</p>
                  <p className="mt-1 text-2xl font-bold text-neutral-900">{formatNumber(dashboard?.pipeline?.processed ?? 0)}</p>
                  <p className="text-xs text-neutral-500">Processed in last known run</p>
                </div>
                <StatusBadge status={dashboard?.pipeline?.status || 'idle'} />
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg border border-neutral-200 bg-white p-4">
                  <p className="text-xs font-medium uppercase text-neutral-500">Created</p>
                  <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(dashboard?.pipeline?.created ?? 0)}</p>
                </div>
                <div className="rounded-lg border border-neutral-200 bg-white p-4">
                  <p className="text-xs font-medium uppercase text-neutral-500">Updated</p>
                  <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(dashboard?.pipeline?.updated ?? 0)}</p>
                </div>
                <div className="rounded-lg border border-neutral-200 bg-white p-4">
                  <p className="text-xs font-medium uppercase text-neutral-500">Last run</p>
                  <p className="mt-2 text-sm font-semibold text-neutral-900">{formatDateTime(dashboard?.pipeline?.last_run)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

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
                  <StatusBadge status={dashboard?.celery?.status || 'degraded'} />
                </div>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-white p-4">
                <p className="text-xs font-medium uppercase text-neutral-500">Workers</p>
                <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(dashboard?.celery?.workers ?? 0)}</p>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-white p-4">
                <p className="text-xs font-medium uppercase text-neutral-500">Active tasks</p>
                <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(dashboard?.celery?.active_tasks ?? 0)}</p>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-white p-4">
                <p className="text-xs font-medium uppercase text-neutral-500">Scheduled</p>
                <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(dashboard?.celery?.scheduled_tasks ?? 0)}</p>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-white p-4">
                <p className="text-xs font-medium uppercase text-neutral-500">Queue length</p>
                <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(dashboard?.celery?.queue_length ?? 0)}</p>
              </div>
              <div className="rounded-lg border border-neutral-200 bg-white p-4">
                <p className="text-xs font-medium uppercase text-neutral-500">Reserved</p>
                <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(dashboard?.celery?.reserved_tasks ?? 0)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Source Monitoring</CardTitle>
            <CardDescription>Per-source run health, duration, errors, and freshness.</CardDescription>
          </CardHeader>
          <CardContent>
            <SourceMonitoringTable data={monitoringSources} />
          </CardContent>
        </Card>
      </div>
    </section>
  );
};

export default DashboardAdminPage;
