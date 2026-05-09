import { Zap } from 'lucide-react';

import {
  clampScore,
  formatRawScore,
  formatScore,
  getScoreMeta,
} from '../services/schedulerService.js';

const toneStyles = {
  green: {
    panel: 'border-green-200 bg-green-50/80',
    badge: 'bg-green-600 text-white',
    text: 'text-green-800',
    bar: 'bg-green-500',
  },
  blue: {
    panel: 'border-blue-200 bg-blue-50/80',
    badge: 'bg-blue-600 text-white',
    text: 'text-blue-800',
    bar: 'bg-blue-500',
  },
  orange: {
    panel: 'border-orange-200 bg-orange-50/80',
    badge: 'bg-orange-500 text-white',
    text: 'text-orange-800',
    bar: 'bg-orange-400',
  },
  red: {
    panel: 'border-red-200 bg-red-50/80',
    badge: 'bg-red-600 text-white',
    text: 'text-red-800',
    bar: 'bg-red-500',
  },
  neutral: {
    panel: 'border-neutral-200 bg-neutral-50',
    badge: 'bg-neutral-600 text-white',
    text: 'text-neutral-800',
    bar: 'bg-neutral-400',
  },
};

const ScoreBadge = ({ metrics }) => {
  const scoreMeta = getScoreMeta(metrics);
  const styles = toneStyles[scoreMeta.tone] || toneStyles.neutral;
  const width = `${clampScore(metrics?.score) * 100}%`;

  return (
    <div
      className={`rounded-lg border p-3 transition-colors duration-200 ${styles.panel}`}
      title={scoreMeta.description}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase text-neutral-500">
            <Zap className="h-3.5 w-3.5" aria-hidden="true" />
            Priority score
          </p>
          <p className={`mt-1 text-sm font-bold ${styles.text}`}>
            Score: {formatScore(metrics?.score)}
            <span className="ml-1 font-medium text-neutral-500">
              (raw: {formatRawScore(metrics?.adaptive_raw_score)})
            </span>
          </p>
        </div>
        <span className={`shrink-0 rounded-md px-2 py-1 text-[11px] font-bold ${styles.badge}`}>
          {scoreMeta.label}
        </span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/80">
        <div
          className={`h-full rounded-full transition-all duration-500 ${styles.bar}`}
          style={{ width }}
        />
      </div>
    </div>
  );
};

export default ScoreBadge;
