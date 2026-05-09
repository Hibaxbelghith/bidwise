import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  Database,
  Server,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import SchedulerPanel from '../../scheduler/components/SchedulerPanel.jsx';
import AlertList from '../dashboard/AlertList.jsx';
import CeleryMonitoringPanel from '../dashboard/CeleryMonitoringPanel.jsx';
import KpiCard from '../dashboard/KpiCard.jsx';
import MetricTile from '../dashboard/MetricTile.jsx';
import MonitoringSummaryGrid from '../dashboard/MonitoringSummaryGrid.jsx';
import PipelineHealthPanel from '../dashboard/PipelineHealthPanel.jsx';
import SourceBarChart from '../dashboard/SourceBarChart.jsx';
import SourceMonitoringTable from '../dashboard/SourceMonitoringTable.jsx';
import SystemStatusPanel from '../dashboard/SystemStatusPanel.jsx';
import { formatNumber, percentFormatter } from '../dashboard/dashboard.Utils.js';

export const ExecutiveDashboardView = ({
  dashboard,
  embeddings,
  logos,
  pipelineLag,
  alerts,
}) => {
  const kpis = [
    {
      title: 'Total Opportunities',
      value: formatNumber(dashboard?.kpis?.total_opportunities ?? 0),
      icon: Database,
    },
    {
      title: 'Success Rate',
      value: `${percentFormatter.format(Number(dashboard?.kpis?.success_rate ?? 0))}%`,
      icon: CheckCircle2,
    },
    {
      title: 'Active Alerts',
      value: formatNumber(alerts.length),
      icon: AlertTriangle,
    },
    {
      title: 'Workers',
      value: formatNumber(dashboard?.celery?.workers ?? 0),
      icon: Server,
    },
  ];

  return (
    <>
      <SystemStatusPanel dashboard={dashboard} />
      <div className="mb-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-4" role="region" aria-label="Executive dashboard statistics">
        {kpis.map((kpi) => (
          <KpiCard key={kpi.title} {...kpi} />
        ))}
      </div>
      <MonitoringSummaryGrid
        embeddings={embeddings}
        logos={logos}
        pipelineLag={pipelineLag}
        alerts={alerts}
      />
    </>
  );
};

export const SchedulerIntelligenceView = () => <SchedulerPanel />;

export const SourcesMonitoringView = ({ sources }) => (
  <Card>
    <CardHeader>
      <CardTitle>Sources Monitoring</CardTitle>
      <CardDescription>Per-source success, errors, duration, and last run.</CardDescription>
    </CardHeader>
    <CardContent>
      <SourceMonitoringTable data={sources} />
    </CardContent>
  </Card>
);

export const PipelineHealthView = ({ dashboard, embeddings, pipelineLag }) => (
  <div className="space-y-6">
    <div className="grid gap-6 xl:grid-cols-2">
      <PipelineHealthPanel pipeline={dashboard?.pipeline} />
      <Card>
        <CardHeader>
          <CardTitle>Backlog</CardTitle>
          <CardDescription>Raw and embedding queues that should drain after ingestion.</CardDescription>
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
          <MetricTile
            label="Missing embeddings"
            value={formatNumber(embeddings.missing_embeddings)}
            detail={`${percentFormatter.format(Number(embeddings.coverage || 0))}% coverage`}
            tone={Number(embeddings.missing_embeddings || 0) > 0 ? 'yellow' : 'green'}
          />
          <MetricTile
            label="Queue length"
            value={formatNumber(dashboard?.celery?.queue_length ?? 0)}
            detail="Active, reserved, and scheduled tasks"
          />
        </CardContent>
      </Card>
    </div>
    <CeleryMonitoringPanel celery={dashboard?.celery} />
  </div>
);

export const AlertsView = ({ alerts }) => (
  <Card>
    <CardHeader>
      <div className="flex items-center gap-3">
        <BellRing className="h-5 w-5 text-blue-600" aria-hidden="true" />
        <div>
          <CardTitle>Alerts</CardTitle>
          <CardDescription>Failures, stale sources, and anomaly signals.</CardDescription>
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <AlertList alerts={alerts} />
    </CardContent>
  </Card>
);

export const AnalyticsView = ({ dashboard }) => (
  <div className="grid gap-6 xl:grid-cols-2">
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
        <CardTitle>Pipeline Trends</CardTitle>
        <CardDescription>Aggregate run totals and throughput.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2">
        <MetricTile
          label="Total runs"
          value={formatNumber(dashboard?.pipeline?.stats?.total_runs)}
          detail="Recorded pipeline runs"
        />
        <MetricTile
          label="Failed runs"
          value={formatNumber(dashboard?.pipeline?.stats?.failed_runs)}
          detail="Runs requiring review"
          tone={Number(dashboard?.pipeline?.stats?.failed_runs || 0) > 0 ? 'yellow' : 'green'}
        />
        <MetricTile
          label="Created"
          value={formatNumber(dashboard?.pipeline?.stats?.total_created)}
          detail="All created records"
          tone="green"
        />
        <MetricTile
          label="Updated"
          value={formatNumber(dashboard?.pipeline?.stats?.total_updated)}
          detail="All refreshed records"
        />
      </CardContent>
    </Card>
  </div>
);
