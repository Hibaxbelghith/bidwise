import { useMemo } from 'react';
import {
  CheckCircle2,
  Clock3,
  Database,
  RadioTower,
  ShieldCheck,
} from 'lucide-react';

import { Badge } from '../../../components/ui/badge.jsx';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../components/ui/card.jsx';
import CeleryMonitoringPanel from './dashboard/CeleryMonitoringPanel.jsx';
import KpiCard from './dashboard/KpiCard.jsx';
import MonitoringSummaryGrid from './dashboard/MonitoringSummaryGrid.jsx';
import PipelineHealthPanel from './dashboard/PipelineHealthPanel.jsx';
import SourceBarChart from './dashboard/SourceBarChart.jsx';
import SourceMonitoringTable from './dashboard/SourceMonitoringTable.jsx';
import SystemStatusPanel from './dashboard/SystemStatusPanel.jsx';
import { formatNumber, percentFormatter } from './dashboard/dashboard.Utils.js';
import { emptyDashboard } from '../hooks/useDashboard.js';

const DashboardAdminContent = ({ dashboard, isLoading, error }) => {
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
  const logos = dashboard?.monitoring?.logos || emptyDashboard.monitoring.logos;
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

        <MonitoringSummaryGrid
          embeddings={embeddings}
          logos={logos}
          pipelineLag={pipelineLag}
          alerts={monitoringAlerts}
        />

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

          <PipelineHealthPanel pipeline={dashboard?.pipeline} />
        </div>

        <CeleryMonitoringPanel celery={dashboard?.celery} />

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

export default DashboardAdminContent;
