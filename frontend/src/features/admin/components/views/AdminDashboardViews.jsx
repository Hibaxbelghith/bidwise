import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  Database,
  FileCheck2,
  LineChart,
  TrendingUp,
  UsersRound,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import SchedulerPanel from '../../scheduler/components/SchedulerPanel.jsx';
import AlertList from '../dashboard/AlertList.jsx';
import AISupervisionPanel from '../dashboard/AISupervisionPanel.jsx';
import CeleryMonitoringPanel from '../dashboard/CeleryMonitoringPanel.jsx';
import KpiCard from '../dashboard/KpiCard.jsx';
import MetricTile from '../dashboard/MetricTile.jsx';
import MonitoringSummaryGrid from '../dashboard/MonitoringSummaryGrid.jsx';
import PipelineHealthPanel from '../dashboard/PipelineHealthPanel.jsx';
import SourceBarChart from '../dashboard/SourceBarChart.jsx';
import SourceMonitoringTable from '../dashboard/SourceMonitoringTable.jsx';
import SystemStatusPanel from '../dashboard/SystemStatusPanel.jsx';
import { formatNumber, percentFormatter } from '../dashboard/dashboard.Utils.js';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const statusLabelKeys = {
  VUE: 'admin.statusViewed',
  INTERESSEE: 'admin.statusInterested',
  POSTULEE_EXTERNEMENT: 'admin.statusApplied',
  ABANDONNEE: 'admin.statusAbandoned',
  ACTIVE: 'admin.statusActive',
  PENDING_REVIEW: 'admin.pendingReview',
  REJECTED: 'admin.rejected',
  EXPIREE: 'admin.expired',
  ARCHIVEE: 'admin.archived',
  EMPLOI: 'admin.jobs',
  STAGE: 'admin.stages',
  SAISONNIER: 'admin.seasonalJobs',
  PROJET: 'admin.callsForTender',
  SUBMITTED: 'admin.statusSubmitted',
  VIEWED_BY_ORGANIZATION: 'admin.statusUnderReview',
  SHORTLISTED: 'admin.statusShortlisted',
  WITHDRAWN: 'admin.statusWithdrawn',
  EXTERNAL_CLICKED: 'admin.statusExternalClicked',
  EXTERNAL_APPLIED_CONFIRMED: 'admin.statusExternalApplied',
  EXTERNAL_REMIND_LATER: 'admin.statusReminderSaved',
  dashboardCandidates: 'admin.candidates',
  dashboardOrganizations: 'admin.organizations',
  dashboardAdmins: 'admin.admins',
  dashboardSuspended: 'admin.statusSuspended',
};

const getStatusLabel = (key, t) => statusLabelKeys[key] ? t(statusLabelKeys[key]) : key;

const formatPercent = (value) => `${percentFormatter.format(Number(value || 0))}%`;
const decimalFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
});
const HIDDEN_ANALYTICS_SOURCES = new Set(['BidWise Recommendation Benchmark']);
const shortDateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
});

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

const CompactLineChart = ({ series, t }) => {
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
        {t('admin.noGrowthDataAvailable')}
      </div>
    );
  }

  const allDates = series
    .flatMap((item) => item.values.map((point) => point?.date))
    .filter(Boolean)
    .map((value) => new Date(value))
    .filter((value) => !Number.isNaN(value.getTime()));

  const startLabel = allDates.length ? shortDateFormatter.format(new Date(Math.min(...allDates.map((value) => value.getTime())))) : '-';
  const endLabel = allDates.length ? shortDateFormatter.format(new Date(Math.max(...allDates.map((value) => value.getTime())))) : '-';

  return (
    <div className="overflow-hidden">
      <svg
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        className="h-44 w-full"
        role="img"
        aria-label={t('admin.platformGrowthChart')}
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
      <div className="mt-2 flex items-center justify-between text-xs text-neutral-500">
        <span>{startLabel}</span>
        <span>{endLabel}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-4">
        {series.map((item) => (
          <div key={item.label} className="flex items-center gap-2 text-sm text-neutral-600">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
            <span>{item.label}</span>
            <span className="text-neutral-400">·</span>
            <span className="font-medium text-neutral-800">
              {formatNumber(item.values[item.values.length - 1]?.count || 0)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const DistributionList = ({ title, data, t }) => {
  const entries = Object.entries(data || {})
    .filter(([, value]) => Number(value || 0) > 0)
    .sort(([, left], [, right]) => Number(right || 0) - Number(left || 0));
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
                <span className="truncate font-medium text-neutral-700">{getStatusLabel(key, t)}</span>
                <span className="text-neutral-500">{formatNumber(value)}</span>
              </div>
              <div className="h-2 rounded-full bg-neutral-100">
                <div className="h-2 rounded-full bg-blue-600" style={{ width }} />
              </div>
            </div>
          );
        }) : (
          <p className="text-sm text-neutral-500">{t('admin.noDataAvailable')}</p>
        )}
      </CardContent>
    </Card>
  );
};

export const GlobalPlatformView = ({ dashboard }) => {
  const { t } = useLanguage();
  const platform = dashboard?.platform || {};
  const users = platform.users || {};
  const applications = platform.applications || {};
  const opportunities = platform.opportunities || {};
  const conversion = platform.conversion || {};
  const growth = platform.growth || {};
  const applicationsPerUser = Number(conversion.applications_per_user || 0);

  const growthSeries = [
    { label: t('admin.users'), color: '#2563eb', values: growth.users || [] },
    { label: t('admin.applications'), color: '#16a34a', values: growth.applications || [] },
    { label: t('admin.opportunities'), color: '#d97706', values: growth.opportunities || [] },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <PlatformKpiCard
          title={t('admin.users')}
          value={formatNumber(users.total)}
          detail={t('admin.newUsersLast30Days', { count: formatNumber(users.new_30_days) })}
          icon={UsersRound}
        />
        <PlatformKpiCard
          title={t('admin.applications')}
          value={formatNumber(applications.total)}
          detail={t('admin.applicationsLast30Days', { count: formatNumber(applications.last_30_days) })}
          icon={FileCheck2}
          tone="green"
        />
        <PlatformKpiCard
          title={t('admin.opportunities')}
          value={formatNumber(opportunities.total)}
          detail={t('admin.activeOpportunitiesCount', { count: formatNumber(opportunities.active) })}
          icon={Database}
          tone="amber"
        />
        <PlatformKpiCard
          title={t('admin.applicationsPerUser')}
          value={decimalFormatter.format(applicationsPerUser)}
          detail={t('admin.applicationsAcrossUsers', {
            applications: formatNumber(applications.total),
            users: formatNumber(users.total),
          })}
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
                <CardTitle>{t('admin.platformGrowth')}</CardTitle>
                <CardDescription>{t('admin.platformGrowthHelp')}</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <CompactLineChart series={growthSeries} t={t} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('admin.recentActivity')}</CardTitle>
            <CardDescription>{t('admin.recentActivityHelp')}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <MetricTile label={t('admin.users7d')} value={formatNumber(users.new_7_days)} detail={t('admin.newAccounts')} />
            <MetricTile label={t('admin.applications7d')} value={formatNumber(applications.last_7_days)} detail={t('admin.candidateActions')} tone="green" />
            <MetricTile label={t('admin.opportunities7d')} value={formatNumber(opportunities.created_7_days)} detail={t('admin.newOpportunityRecords')} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <DistributionList
          title={t('admin.users')}
          t={t}
          data={{
            dashboardCandidates: users.candidates,
            dashboardOrganizations: users.organizations,
            dashboardAdmins: users.admins,
            dashboardSuspended: users.suspended,
          }}
        />
        <DistributionList title={t('admin.applicationsByStatus')} data={applications.by_status} t={t} />
        <DistributionList title={t('admin.opportunitiesByType')} data={opportunities.by_type} t={t} />
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
  const { t } = useLanguage();
  const kpis = [
    {
      title: t('admin.totalOpportunities'),
      value: formatNumber(dashboard?.kpis?.total_opportunities ?? 0),
      icon: Database,
    },
    {
      title: t('admin.contentChangeRate'),
      value: `${percentFormatter.format(Number(dashboard?.kpis?.change_rate ?? 0))}%`,
      icon: CheckCircle2,
      detail: t('admin.successfulRunsPercent', { percent: percentFormatter.format(Number(dashboard?.kpis?.run_success_rate ?? 0)) }),
    },
    {
      title: t('admin.successfulRuns'),
      value: `${percentFormatter.format(Number(dashboard?.kpis?.run_success_rate ?? 0))}%`,
      icon: CheckCircle2,
    },
    {
      title: t('admin.activeAlerts'),
      value: formatNumber(alerts.length),
      icon: AlertTriangle,
    },
  ];

  return (
    <>
      <SystemStatusPanel dashboard={dashboard} />
      <div className="mb-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-4" role="region" aria-label={t('admin.executiveDashboardStats')}>
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
      <div className="mt-8">
        <AISupervisionPanel aiSupervision={dashboard?.ai_supervision} />
      </div>
    </>
  );
};

export const SchedulerIntelligenceView = () => <SchedulerPanel />;

export const SourcesMonitoringView = ({ sources }) => (
  <Card>
    <CardHeader>
      <TranslatedSourcesHeader />
    </CardHeader>
    <CardContent>
      <SourceMonitoringTable data={sources} />
    </CardContent>
  </Card>
);

const TranslatedSourcesHeader = () => {
  const { t } = useLanguage();
  return (
    <>
      <CardTitle>{t('admin.sourcesMonitoring')}</CardTitle>
      <CardDescription>{t('admin.sourcesMonitoringHelp')}</CardDescription>
    </>
  );
};

export const PipelineHealthView = ({ dashboard, embeddings, pipelineLag }) => {
  const { t } = useLanguage();
  return (
  <div className="space-y-6">
    <div className="grid gap-6 xl:grid-cols-2">
      <PipelineHealthPanel pipeline={dashboard?.pipeline} />
      <Card>
        <CardHeader>
          <CardTitle>{t('admin.backlog')}</CardTitle>
          <CardDescription>{t('admin.backlogHelp')}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <MetricTile
            label={t('admin.newRaw')}
            value={formatNumber(pipelineLag.new_raw_remaining)}
            detail={pipelineLag.backlog_detected ? t('admin.backlogDetected') : t('admin.noBacklog')}
            tone={pipelineLag.backlog_detected ? 'red' : 'green'}
          />
          <MetricTile
            label={t('admin.rawTotal')}
            value={formatNumber(pipelineLag.raw_total)}
            detail={t('admin.allRawRecords')}
          />
          <MetricTile
            label={t('admin.missingEmbeddings')}
            value={formatNumber(embeddings.missing_embeddings)}
            detail={t('admin.coveragePercent', { percent: percentFormatter.format(Number(embeddings.coverage || 0)) })}
            tone={Number(embeddings.missing_embeddings || 0) > 0 ? 'yellow' : 'green'}
          />
          <MetricTile
            label={t('admin.queueLength')}
            value={formatNumber(dashboard?.celery?.queue_length ?? 0)}
            detail={t('admin.queueLengthHelp')}
          />
        </CardContent>
      </Card>
    </div>
    <CeleryMonitoringPanel celery={dashboard?.celery} />
  </div>
  );
};

export const AlertsView = ({ alerts }) => {
  const { t } = useLanguage();
  return (
  <Card>
    <CardHeader>
      <div className="flex items-center gap-3">
        <BellRing className="h-5 w-5 text-blue-600" aria-hidden="true" />
        <div>
          <CardTitle>{t('admin.alerts')}</CardTitle>
          <CardDescription>{t('admin.alertsHelp')}</CardDescription>
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <AlertList alerts={alerts} />
    </CardContent>
  </Card>
  );
};

export const AnalyticsView = ({ dashboard }) => {
  const { t } = useLanguage();
  const analyticsSources = (dashboard?.sources || []).filter(
    (source) => !HIDDEN_ANALYTICS_SOURCES.has(String(source?.name || '').trim())
  );

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>{t('admin.opportunitiesBySource')}</CardTitle>
          <CardDescription>{t('admin.opportunitiesBySourceHelp')}</CardDescription>
        </CardHeader>
        <CardContent>
          <SourceBarChart data={analyticsSources} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t('admin.pipelineHistory')}</CardTitle>
          <CardDescription>{t('admin.pipelineHistoryHelp')}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <MetricTile
            label={t('admin.runsRecorded')}
            value={formatNumber(dashboard?.pipeline?.stats?.total_runs)}
            detail={t('admin.runsRecordedHelp')}
          />
          <MetricTile
            label={t('admin.runsFailed')}
            value={formatNumber(dashboard?.pipeline?.stats?.failed_runs)}
            detail={t('admin.runsFailedHelp')}
            tone={Number(dashboard?.pipeline?.stats?.failed_runs || 0) > 0 ? 'yellow' : 'green'}
          />
          <MetricTile
            label={t('admin.averageChangeRate')}
            value={`${percentFormatter.format(Number(dashboard?.pipeline?.stats?.change_rate || 0))}%`}
            detail={t('admin.averageChangeRateHelp')}
            tone="green"
          />
          <MetricTile
            label={t('admin.runSuccess')}
            value={`${percentFormatter.format(Number(dashboard?.pipeline?.stats?.run_success_rate || 0))}%`}
            detail={t('admin.runSuccessHelp')}
          />
        </CardContent>
      </Card>
    </div>
  );
};
