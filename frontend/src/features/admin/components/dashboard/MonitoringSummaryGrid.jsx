import {
  AlertTriangle,
  BellRing,
  Cpu,
  Image as ImageIcon,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import AlertList from './AlertList.jsx';
import MetricTile from './MetricTile.jsx';
import { formatNumber, percentFormatter } from './dashboard.Utils.js';

const SectionHeader = ({ title, description }) => (
  <div className="space-y-1">
    <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-700">{title}</h3>
    <p className="text-sm text-neutral-500">{description}</p>
  </div>
);

const MonitoringSummaryGrid = ({ embeddings, logos, pipelineLag, alerts }) => {
  const logoCoverage = Number(logos.coverage || 0);
  const logoTotal = Number(logos.total || 0);
  const criticalAlerts = alerts.filter((alert) => alert?.severity === 'CRITICAL').length;
  const warningAlerts = alerts.filter((alert) => alert?.severity === 'WARNING').length;
  const infoAlerts = alerts.filter((alert) => alert?.severity === 'INFO').length;
  const alertSummary = alerts.length
    ? `${formatNumber(criticalAlerts)} critical · ${formatNumber(warningAlerts)} warning${infoAlerts ? ` · ${formatNumber(infoAlerts)} info` : ''}`
    : 'No active issue';

  return (
    <div className="mb-8 space-y-8">
      <section className="space-y-4" aria-label="Operational signals">
        <SectionHeader
          title="Operational Signals"
          description="Live runtime indicators that help confirm whether ingestion and monitoring are healthy right now."
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>Pipeline Lag</CardTitle>
                  <CardDescription>Backlog signals that should return to normal after a complete ingestion cycle.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <MetricTile
                label="New raw backlog"
                value={formatNumber(pipelineLag.new_raw_remaining)}
                detail={pipelineLag.backlog_detected ? 'New raw records are still waiting to be processed' : 'No backlog detected after the latest run'}
                tone={pipelineLag.backlog_detected ? 'red' : 'green'}
              />
              <MetricTile
                label="Raw inventory"
                value={formatNumber(pipelineLag.raw_total)}
                detail="Total raw records stored for ingestion history"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <BellRing className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>Active Alerts</CardTitle>
                  <CardDescription>Current anomaly signals for pipeline freshness, failures, and source monitoring.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className={`rounded-lg border p-4 text-sm font-medium ${criticalAlerts ? 'border-red-200 bg-red-50 text-red-800' : warningAlerts ? 'border-yellow-200 bg-yellow-50 text-yellow-800' : 'border-green-200 bg-green-50 text-green-800'}`}>
                {alertSummary}
              </div>
              <AlertList alerts={alerts} />
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="space-y-4" aria-label="Coverage health">
        <SectionHeader
          title="Coverage Health"
          description="Platform readiness indicators for AI features and company media completeness. These metrics are quality signals, not live incidents."
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Cpu className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>AI Readiness</CardTitle>
                  <CardDescription>Embedding coverage required by match scoring and similar opportunity features.</CardDescription>
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
                <ImageIcon className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>Media Coverage</CardTitle>
                  <CardDescription>Company logo extraction coverage across scraped opportunities.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <MetricTile
                label="With logo"
                value={`${percentFormatter.format(logoCoverage)}%`}
                detail={`${formatNumber(logos.with_logo)} / ${formatNumber(logos.total)}`}
                tone={logoTotal === 0 ? 'neutral' : logoCoverage >= 80 ? 'green' : 'yellow'}
              />
              <MetricTile
                label="Placeholder"
                value={formatNumber(logos.missing_or_placeholder)}
                detail="Missing or anonymous company logo"
                tone={Number(logos.missing_or_placeholder || 0) > 0 ? 'yellow' : 'green'}
              />
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default MonitoringSummaryGrid;
