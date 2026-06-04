import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  Database,
  FileCheck2,
  LineChart,
  Server,
  TrendingUp,
  UsersRound,
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

const statusLabels = {
  VUE: 'Vues',
  INTERESSEE: 'Interessees',
  POSTULEE_EXTERNEMENT: 'Postulees',
  ABANDONNEE: 'Abandonnees',
  ACTIVE: 'Actives',
  EXPIREE: 'Expirees',
  ARCHIVEE: 'Archivees',
  EMPLOI: 'Emplois',
  STAGE: 'Stages',
  SAISONNIER: 'Saisonniers',
  PROJET: 'Calls for tender',
};

const formatPercent = (value) => `${percentFormatter.format(Number(value || 0))}%`;

const PlatformKpiCard = ({ title, value, detail, icon: Icon, tone = 'blue' }) => {
  const tones = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    amber: 'bg-yellow-50 text-yellow-700',
    neutral: 'bg-neutral-100 text-neutral-700',
  };

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium text-neutral-600">{title}</p>
            <p className="mt-3 text-3xl font-bold text-neutral-950">{value}</p>
            <p className="mt-2 text-sm text-neutral-500">{detail}</p>
          </div>
          <div className={`rounded-md p-2 ${tones[tone] || tones.blue}`}>
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const CompactLineChart = ({ series }) => {
  const maxValue = Math.max(
    ...series.flatMap((item) => item.values.map((point) => Number(point.count || 0))),
    0
  );
  const chartHeight = 160;
  const chartWidth = 580;
  const safeMax = maxValue || 1;

  if (!series.some((item) => item.values.length)) {
    return (
      <div className="flex h-44 items-center justify-center rounded-md border border-dashed border-neutral-200 text-sm text-neutral-500">
        No growth data available
      </div>
    );
  }

  return (
    <div className="overflow-hidden">
      <svg
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        className="h-44 w-full"
        role="img"
        aria-label="30 day platform growth chart"
        preserveAspectRatio="none"
      >
        {[0, 1, 2, 3].map((line) => {
          const y = 12 + (line * (chartHeight - 24)) / 3;
          return <line key={line} x1="0" x2={chartWidth} y1={y} y2={y} stroke="#e5e7eb" strokeWidth="1" />;
        })}
        {series.map((item) => {
          const lastIndex = Math.max(item.values.length - 1, 1);
          const points = item.values
            .map((point, index) => {
              const x = (index / lastIndex) * chartWidth;
              const y = chartHeight - 12 - (Number(point.count || 0) / safeMax) * (chartHeight - 24);
              return `${x},${y}`;
            })
            .join(' ');

          return (
            <polyline
              key={item.label}
              points={points}
              fill="none"
              stroke={item.color}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
      <div className="mt-3 flex flex-wrap gap-4">
        {series.map((item) => (
          <div key={item.label} className="flex items-center gap-2 text-sm text-neutral-600">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
            {item.label}
          </div>
        ))}
      </div>
    </div>
  );
};

const DistributionList = ({ title, data }) => {
  const entries = Object.entries(data || {}).filter(([, value]) => Number(value || 0) > 0);
  const maxValue = Math.max(...entries.map(([, value]) => Number(value || 0)), 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {entries.length ? entries.map(([key, value]) => {
          const width = `${Math.max((Number(value || 0) / maxValue) * 100, 4)}%`;
          return (
            <div key={key} className="space-y-2">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="truncate font-medium text-neutral-700">{statusLabels[key] || key}</span>
                <span className="text-neutral-500">{formatNumber(value)}</span>
              </div>
              <div className="h-2 rounded-full bg-neutral-100">
                <div className="h-2 rounded-full bg-blue-600" style={{ width }} />
              </div>
            </div>
          );
        }) : (
          <p className="text-sm text-neutral-500">No data available</p>
        )}
      </CardContent>
    </Card>
  );
};

export const GlobalPlatformView = ({ dashboard }) => {
  const platform = dashboard?.platform || {};
  const users = platform.users || {};
  const applications = platform.applications || {};
  const opportunities = platform.opportunities || {};
  const conversion = platform.conversion || {};
  const growth = platform.growth || {};

  const growthSeries = [
    { label: 'Utilisateurs', color: '#2563eb', values: growth.users || [] },
    { label: 'Candidatures', color: '#16a34a', values: growth.applications || [] },
    { label: 'Opportunites', color: '#d97706', values: growth.opportunities || [] },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <PlatformKpiCard
          title="Utilisateurs"
          value={formatNumber(users.total)}
          detail={`${formatNumber(users.new_30_days)} nouveaux sur 30 jours`}
          icon={UsersRound}
        />
        <PlatformKpiCard
          title="Candidatures"
          value={formatNumber(applications.total)}
          detail={`${formatNumber(applications.last_30_days)} sur 30 jours`}
          icon={FileCheck2}
          tone="green"
        />
        <PlatformKpiCard
          title="Opportunites"
          value={formatNumber(opportunities.total)}
          detail={`${formatNumber(opportunities.active)} actives`}
          icon={Database}
          tone="amber"
        />
        <PlatformKpiCard
          title="Taux candidature"
          value={formatPercent(conversion.application_rate)}
          detail={`${percentFormatter.format(conversion.applications_per_user)} candidature / utilisateur`}
          icon={TrendingUp}
          tone="neutral"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.7fr)]">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <LineChart className="h-5 w-5 text-blue-600" aria-hidden="true" />
              <div>
                <CardTitle>Croissance plateforme</CardTitle>
                <CardDescription>Evolution quotidienne des utilisateurs, candidatures et opportunites.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <CompactLineChart series={growthSeries} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Utilisation recente</CardTitle>
            <CardDescription>Fenetres glissantes pour suivre le rythme de croissance.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <MetricTile label="Utilisateurs 7j" value={formatNumber(users.new_7_days)} detail="Nouveaux comptes" />
            <MetricTile label="Candidatures 7j" value={formatNumber(applications.last_7_days)} detail="Actions candidats" tone="green" />
            <MetricTile label="Opportunites 7j" value={formatNumber(opportunities.created_7_days)} detail="Nouveaux contenus" />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <DistributionList
          title="Utilisateurs"
          data={{
            Candidats: users.candidates,
            Organisations: users.organizations,
            Admins: users.admins,
            Suspendus: users.suspended,
          }}
        />
        <DistributionList title="Candidatures par statut" data={applications.by_status} />
        <DistributionList title="Opportunites par type" data={opportunities.by_type} />
      </div>
    </div>
  );
};

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
