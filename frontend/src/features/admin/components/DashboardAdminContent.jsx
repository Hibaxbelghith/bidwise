import { Navigate, useParams } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';

import { Badge } from '../../../components/ui/badge.jsx';
import { Card, CardContent } from '../../../components/ui/card.jsx';
import {
  AlertsView,
  AnalyticsView,
  ExecutiveDashboardView,
  GlobalPlatformView,
  PipelineHealthView,
  SchedulerIntelligenceView,
  SourcesMonitoringView,
} from './views/AdminDashboardViews.jsx';
import { emptyDashboard } from '../hooks/useDashboard.js';

const viewTitles = {
  dashboard: 'Vue globale',
  operations: 'Operations Monitoring',
  sources: 'Sources Monitoring',
  scheduler: 'Scheduler Intelligence',
  pipeline: 'Pipeline Health',
  alerts: 'Alerts',
  analytics: 'Analytics',
};

const validViews = new Set(Object.keys(viewTitles));

const DashboardSkeleton = () => (
  <section className="min-h-[calc(100vh-4rem)] bg-neutral-50 px-4 py-8 sm:px-6 lg:px-8" aria-labelledby="admin-dashboard-heading">
    <div className="mx-auto max-w-7xl">
      <div className="mb-8">
        <div className="mb-3 h-9 w-72 animate-pulse rounded-md bg-neutral-200" />
        <div className="h-5 w-96 max-w-full animate-pulse rounded-md bg-neutral-200" />
      </div>
      <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
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

const DashboardAdminContent = ({ dashboard, isLoading, error }) => {
  const { dashboardView } = useParams();
  const activeView = dashboardView || 'dashboard';
  const embeddings = dashboard?.monitoring?.embeddings || emptyDashboard.monitoring.embeddings;
  const logos = dashboard?.monitoring?.logos || emptyDashboard.monitoring.logos;
  const pipelineLag = dashboard?.monitoring?.pipeline_lag || emptyDashboard.monitoring.pipeline_lag;
  const monitoringSources = dashboard?.monitoring?.sources || [];
  const monitoringAlerts = dashboard?.monitoring?.alerts || [];

  if (!validViews.has(activeView)) {
    return <Navigate to="/admin/dashboard" replace />;
  }

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  const renderView = () => {
    switch (activeView) {
      case 'sources':
        return <SourcesMonitoringView sources={monitoringSources} />;
      case 'scheduler':
        return <SchedulerIntelligenceView />;
      case 'pipeline':
        return <PipelineHealthView dashboard={dashboard} embeddings={embeddings} pipelineLag={pipelineLag} />;
      case 'alerts':
        return <AlertsView alerts={monitoringAlerts} />;
      case 'analytics':
        return <AnalyticsView dashboard={dashboard} />;
      case 'operations':
        return (
          <ExecutiveDashboardView
            dashboard={dashboard}
            embeddings={embeddings}
            logos={logos}
            pipelineLag={pipelineLag}
            alerts={monitoringAlerts}
          />
        );
      case 'dashboard':
      default:
        return <GlobalPlatformView dashboard={dashboard} />;
    }
  };

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-neutral-50 px-4 py-8 sm:px-6 lg:px-8" aria-labelledby="admin-dashboard-heading">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <h1 id="admin-dashboard-heading" className="text-3xl font-bold text-neutral-900">
              {viewTitles[activeView]}
            </h1>

          </div>
        </div>

        {error ? (
          <Card className="mb-8 border-red-200 bg-red-50">
            <CardContent className="p-6">
              <p className="font-medium text-red-800">{error}</p>
            </CardContent>
          </Card>
        ) : null}

        {renderView()}
      </div>
    </section>
  );
};

export default DashboardAdminContent;
