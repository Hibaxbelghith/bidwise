import { useMemo } from 'react';
import { AlertCircle, CalendarClock, Gauge, RadioTower, ShieldAlert, Zap } from 'lucide-react';

import { Card, CardContent } from '../../../../components/ui/card.jsx';
import { useScheduler } from '../hooks/useScheduler.js';
import {
  formatRelativeTime,
  getSchedulerSummary,
} from '../services/schedulerService.js';
import SchedulerCard from './SchedulerCard.jsx';

const summaryItems = [
  {
    key: 'sourceCount',
    label: 'Sources',
    icon: RadioTower,
    tone: 'text-blue-700 bg-blue-50 border-blue-100',
  },
  {
    key: 'highPriorityCount',
    label: 'High priority',
    icon: Zap,
    tone: 'text-green-700 bg-green-50 border-green-100',
  },
  {
    key: 'attentionCount',
    label: 'Needs attention',
    icon: ShieldAlert,
    tone: 'text-red-700 bg-red-50 border-red-100',
  },
  {
    key: 'nextRunAt',
    label: 'Next run',
    icon: Gauge,
    tone: 'text-yellow-800 bg-yellow-50 border-yellow-100',
  },
];

const SchedulerSkeleton = () => (
  <div className="grid gap-4 lg:grid-cols-2">
    {[0, 1, 2, 3].map((item) => (
      <Card key={item} className="border-neutral-200">
        <CardContent className="space-y-4 p-6">
          <div className="h-7 w-40 animate-pulse rounded-md bg-neutral-200" />
          <div className="h-20 animate-pulse rounded-lg bg-neutral-100" />
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="h-20 animate-pulse rounded-lg bg-neutral-100" />
            <div className="h-20 animate-pulse rounded-lg bg-neutral-100" />
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

const SchedulerPanel = () => {
  const { schedulerState, isLoading, error } = useScheduler();
  const summary = useMemo(() => getSchedulerSummary(schedulerState), [schedulerState]);

  return (
    <section className="mb-8" aria-labelledby="scheduler-state-heading">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex items-start gap-3">
          <span className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
            <CalendarClock className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h2 id="scheduler-state-heading" className="text-xl font-bold text-neutral-950">
              Adaptive Scheduler
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-neutral-600">
              Source cadence, priority score, next run, and the metric signals behind each scheduler decision.
            </p>
          </div>
        </div>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {summaryItems.map((item) => {
          const Icon = item.icon;
          const value = item.key === 'nextRunAt'
            ? formatRelativeTime(summary.nextRunAt)
            : summary[item.key];

          return (
            <div key={item.key} className={`rounded-lg border p-4 ${item.tone}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase">{item.label}</p>
                <Icon className="h-4 w-4" aria-hidden="true" />
              </div>
              {isLoading ? (
                <div className="mt-3 h-7 w-20 animate-pulse rounded-md bg-white/70" />
              ) : (
                <p className="mt-2 text-2xl font-bold">{value}</p>
              )}
            </div>
          );
        })}
      </div>

      {error ? (
        <Card className="mb-4 border-red-200 bg-red-50">
          <CardContent className="flex items-center gap-3 p-4 text-sm font-medium text-red-800">
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            {error}
          </CardContent>
        </Card>
      ) : null}

      {isLoading ? <SchedulerSkeleton /> : null}

      {!isLoading && !schedulerState.length ? (
        <div className="rounded-lg border border-dashed border-neutral-200 bg-white p-6 text-sm text-neutral-500">
          No scheduler decisions available.
        </div>
      ) : null}

      {!isLoading && schedulerState.length ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {schedulerState.map((decision) => (
            <SchedulerCard key={decision.source} decision={decision} />
          ))}
        </div>
      ) : null}
    </section>
  );
};

export default SchedulerPanel;
