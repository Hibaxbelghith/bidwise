import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';

import { getTrendMeta } from '../services/schedulerService.js';
import Sparkline from './Sparkline.jsx';

const toneStyles = {
  green: {
    shell: 'border-green-200 bg-green-50 text-green-800',
    bar: 'bg-green-500',
    muted: 'bg-green-200',
  },
  blue: {
    shell: 'border-blue-200 bg-blue-50 text-blue-800',
    bar: 'bg-blue-500',
    muted: 'bg-blue-200',
  },
  orange: {
    shell: 'border-orange-200 bg-orange-50 text-orange-800',
    bar: 'bg-orange-500',
    muted: 'bg-orange-200',
  },
  red: {
    shell: 'border-red-200 bg-red-50 text-red-800',
    bar: 'bg-red-500',
    muted: 'bg-red-200',
  },
  neutral: {
    shell: 'border-neutral-200 bg-neutral-50 text-neutral-700',
    bar: 'bg-neutral-400',
    muted: 'bg-neutral-200',
  },
};

const iconMap = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: ArrowRight,
};

const TrendIndicator = ({ decision }) => {
  const trend = getTrendMeta(decision);
  const styles = toneStyles[trend.tone] || toneStyles.blue;
  const Icon = iconMap[trend.direction] || ArrowRight;
  const values = decision?.metrics?.trend || [];

  return (
    <div className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 ${styles.shell}`}>
      <div className="flex min-w-0 items-center gap-2">
        <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="truncate text-sm font-semibold">{trend.label}</span>
      </div>
      <div className="shrink-0">
        <Sparkline values={values} tone={trend.tone} label="Created trend" />
      </div>
    </div>
  );
};

export default TrendIndicator;
