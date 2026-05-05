import { Activity, Clock3, Info } from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import {
  formatRelativeTime,
  formatSourceName,
  getDecisionBadges,
  getDecisionModeMeta,
  getReasonMeta,
} from '../services/schedulerService.js';
import MetricsGrid from './MetricsGrid.jsx';
import ScoreBadge from './ScoreBadge.jsx';
import StatusBadge from './StatusBadge.jsx';
import TrendIndicator from './TrendIndicator.jsx';

const modeStyles = {
  green: 'border-green-200 bg-green-50 text-green-700',
  blue: 'border-blue-200 bg-blue-50 text-blue-700',
  red: 'border-red-200 bg-red-50 text-red-700',
  neutral: 'border-neutral-200 bg-neutral-50 text-neutral-700',
};

const reasonStyles = {
  green: 'border-green-200 bg-green-50 text-green-700',
  yellow: 'border-yellow-200 bg-yellow-50 text-yellow-800',
  red: 'border-red-200 bg-red-50 text-red-700',
  blue: 'border-blue-200 bg-blue-50 text-blue-700',
};

const ReasonPill = ({ reason }) => {
  const reasonMeta = getReasonMeta(reason);

  return (
    <span className="group relative inline-flex" tabIndex={0} aria-label={`${reasonMeta.label}: ${reasonMeta.tooltip}`}>
      <Badge
        variant="outline"
        className={`max-w-full gap-1.5 ${reasonStyles[reasonMeta.tone] || reasonStyles.blue}`}
      >
        <Info className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span className="truncate">{reasonMeta.label}</span>
      </Badge>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-20 mb-2 w-56 rounded-md bg-neutral-900 px-2.5 py-2 text-xs font-medium normal-case text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus:opacity-100"
      >
        {reasonMeta.tooltip}
      </span>
    </span>
  );
};

const SchedulerCard = ({ decision }) => {
  const source = formatSourceName(decision?.source);
  const mode = getDecisionModeMeta(decision);
  const badges = getDecisionBadges(decision);

  return (
    <Card className="overflow-hidden border-neutral-200 bg-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-lg">
      <CardHeader className="gap-4 border-b border-neutral-100 bg-neutral-50/70 pb-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <CardTitle className="truncate text-base font-bold text-neutral-950">
              {source}
            </CardTitle>
            <p className="mt-1 text-xs font-medium uppercase text-neutral-500">
              Final scheduler decision
            </p>
          </div>
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
            <Activity className="h-5 w-5" aria-hidden="true" />
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className={modeStyles[mode.tone] || modeStyles.neutral}>
            {mode.label}
          </Badge>
          <ReasonPill reason={decision?.reason} />
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-5">
        <div className="rounded-lg border border-blue-200 bg-blue-50/70 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-blue-700">
            <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
            Next run
          </div>
          <p className="mt-1 text-xl font-bold text-blue-950">
            {formatRelativeTime(decision?.next_run_at)}
          </p>
        </div>

        <ScoreBadge metrics={decision?.metrics} />

        <div className="flex flex-wrap gap-2">
          {badges.map((badge) => (
            <StatusBadge key={badge.type} badge={badge} />
          ))}
        </div>

        <TrendIndicator decision={decision} />
        <MetricsGrid decision={decision} />
      </CardContent>
    </Card>
  );
};

export default SchedulerCard;
