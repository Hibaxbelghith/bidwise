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

const MonitoringSummaryGrid = ({ embeddings, logos, pipelineLag, alerts }) => {
  const logoCoverage = Number(logos.coverage || 0);
  const logoTotal = Number(logos.total || 0);

  return (
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
            <ImageIcon className="h-5 w-5 text-blue-600" aria-hidden="true" />
            <div>
              <CardTitle>Media Coverage</CardTitle>
              <CardDescription>Company logo extraction coverage from scraped opportunities.</CardDescription>
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
          <AlertList alerts={alerts} />
        </CardContent>
      </Card>
    </div>
  );
};

export default MonitoringSummaryGrid;
