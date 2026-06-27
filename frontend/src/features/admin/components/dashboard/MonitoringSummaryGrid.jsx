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
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const SectionHeader = ({ title, description }) => (
  <div className="space-y-1">
    <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-700">{title}</h3>
    <p className="text-sm text-neutral-500">{description}</p>
  </div>
);

const MonitoringSummaryGrid = ({ embeddings, logos, pipelineLag, alerts }) => {
  const { t } = useLanguage();
  const logoCoverage = Number(logos.coverage || 0);
  const logoTotal = Number(logos.total || 0);
  const criticalAlerts = alerts.filter((alert) => alert?.severity === 'CRITICAL').length;
  const warningAlerts = alerts.filter((alert) => alert?.severity === 'WARNING').length;
  const infoAlerts = alerts.filter((alert) => alert?.severity === 'INFO').length;
  const alertSummary = alerts.length
    ? `${formatNumber(criticalAlerts)} critical · ${formatNumber(warningAlerts)} warning${infoAlerts ? ` · ${formatNumber(infoAlerts)} info` : ''}`
    : t('admin.noActiveIssue');
  const localizedAlertSummary = alerts.length
    ? [
      t('admin.criticalCount', { count: formatNumber(criticalAlerts) }),
      t('admin.warningCount', { count: formatNumber(warningAlerts) }),
      infoAlerts ? t('admin.infoCount', { count: formatNumber(infoAlerts) }) : null,
    ].filter(Boolean).join(' · ')
    : t('admin.noActiveIssue');

  return (
    <div className="mb-8 space-y-8">
      <section className="space-y-4" aria-label={t('admin.operationalSignals')}>
        <SectionHeader
          title={t('admin.operationalSignals')}
          description={t('admin.operationalSignalsHelp')}
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>{t('admin.pipelineLag')}</CardTitle>
                  <CardDescription>{t('admin.pipelineLagHelp')}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <MetricTile
                label={t('admin.newRawBacklog')}
                value={formatNumber(pipelineLag.new_raw_remaining)}
                detail={pipelineLag.backlog_detected ? t('admin.newRawWaiting') : t('admin.noBacklogAfterLatestRun')}
                tone={pipelineLag.backlog_detected ? 'red' : 'green'}
              />
              <MetricTile
                label={t('admin.rawInventory')}
                value={formatNumber(pipelineLag.raw_total)}
                detail={t('admin.rawInventoryHelp')}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <BellRing className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>{t('admin.activeAlerts')}</CardTitle>
                  <CardDescription>{t('admin.activeAlertsHelp')}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className={`rounded-lg border p-4 text-sm font-medium ${criticalAlerts ? 'border-red-200 bg-red-50 text-red-800' : warningAlerts ? 'border-yellow-200 bg-yellow-50 text-yellow-800' : 'border-green-200 bg-green-50 text-green-800'}`}>
                {localizedAlertSummary}
              </div>
              <AlertList alerts={alerts} />
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="space-y-4" aria-label={t('admin.coverageHealth')}>
        <SectionHeader
          title={t('admin.coverageHealth')}
          description={t('admin.coverageHealthHelp')}
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Cpu className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>{t('admin.aiReadiness')}</CardTitle>
                  <CardDescription>{t('admin.aiReadinessHelp')}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-3">
              <MetricTile
                label={t('admin.coverage')}
                value={`${percentFormatter.format(Number(embeddings.coverage || 0))}%`}
                detail={`${formatNumber(embeddings.with_embeddings)} / ${formatNumber(embeddings.total)}`}
                tone={embeddings.is_complete ? 'green' : 'yellow'}
              />
              <MetricTile
                label={t('admin.missing')}
                value={formatNumber(embeddings.missing_embeddings)}
                detail={t('admin.opportunitiesWithoutVectors')}
                tone={Number(embeddings.missing_embeddings || 0) > 0 ? 'yellow' : 'green'}
              />
              <MetricTile
                label="pgvector"
                value={formatNumber(embeddings.with_pg_embeddings)}
                detail={t('admin.indexedVectorPayloads')}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <ImageIcon className="h-5 w-5 text-blue-600" aria-hidden="true" />
                <div>
                  <CardTitle>{t('admin.mediaCoverage')}</CardTitle>
                  <CardDescription>{t('admin.mediaCoverageHelp')}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <MetricTile
                label={t('admin.withLogo')}
                value={`${percentFormatter.format(logoCoverage)}%`}
                detail={`${formatNumber(logos.with_logo)} / ${formatNumber(logos.total)}`}
                tone={logoTotal === 0 ? 'neutral' : logoCoverage >= 80 ? 'green' : 'yellow'}
              />
              <MetricTile
                label={t('admin.placeholder')}
                value={formatNumber(logos.missing_or_placeholder)}
                detail={t('admin.missingAnonymousLogo')}
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
