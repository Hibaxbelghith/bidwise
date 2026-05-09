import { Activity, Ban, CircleSlash, RefreshCw, TimerReset, Waves } from 'lucide-react';

import {
  formatDuration,
  formatMetricNumber,
  formatPercent,
} from '../services/schedulerService.js';

const MetricsGrid = ({ decision }) => {
  const metrics = decision?.metrics || {};
  const items = [
    {
      label: 'Created avg (EMA)',
      value: formatMetricNumber(metrics.created_avg),
      icon: Activity,
      tone: 'text-green-700 bg-green-50',
    },
    {
      label: 'Updated avg (EMA)',
      value: formatMetricNumber(metrics.updated_avg),
      icon: RefreshCw,
      tone: 'text-blue-700 bg-blue-50',
    },
    {
      label: 'Created / run',
      value: formatMetricNumber(metrics.created_per_run),
      icon: Waves,
      tone: 'text-green-700 bg-green-50',
    },
    {
      label: 'Failure rate',
      value: formatPercent(metrics.failure_rate),
      icon: Ban,
      tone: 'text-red-700 bg-red-50',
    },
    {
      label: 'Zero runs',
      value: formatMetricNumber(metrics.zero_runs),
      icon: CircleSlash,
      tone: 'text-yellow-800 bg-yellow-50',
    },
    {
      label: 'Interval',
      value: formatDuration(decision?.interval_seconds),
      icon: TimerReset,
      tone: 'text-blue-700 bg-blue-50',
    },
    {
      label: 'Freshness lag',
      value: formatDuration(metrics.freshness_lag),
      icon: TimerReset,
      tone: 'text-yellow-800 bg-yellow-50',
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => {
        const Icon = item.icon;

        return (
          <div key={item.label} className="rounded-lg border border-neutral-200 bg-white p-3">
            <div className="flex items-center gap-2">
              <span className={`flex h-7 w-7 items-center justify-center rounded-md ${item.tone}`}>
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              <p className="text-[11px] font-semibold uppercase text-neutral-500">{item.label}</p>
            </div>
            <p className="mt-2 text-lg font-bold text-neutral-900">{item.value}</p>
          </div>
        );
      })}
    </div>
  );
};

export default MetricsGrid;
