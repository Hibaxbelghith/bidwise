const numberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
});

const percentFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
});

const emptyMetrics = {
  created_avg: 0,
  updated_avg: 0,
  failure_rate: 0,
  zero_runs: 0,
  freshness_lag: null,
  created_per_run: 0,
  trend: [],
  score: null,
  adaptive_raw_score: null,
};

const highVolumeReasons = new Set([
  'HIGH_ACTIVITY',
  'HIGH_VOLUME',
  'ADAPTIVE_HIGH_CREATED_VOLUME',
  'ADAPTIVE_HIGH_UPDATED_VOLUME',
  'ADAPTIVE_SCORE_HIGH_ACTIVITY',
]);

const cooldownReasons = new Set([
  'ADAPTIVE_FAILURE_BACKOFF',
  'ADAPTIVE_HARD_FAILURE_COOLDOWN',
  'ADAPTIVE_LOW_VOLUME',
  'ADAPTIVE_RECENT_FAILURES',
  'ADAPTIVE_SCORE_COOLDOWN',
  'RETRY_AFTER_FAILURE',
  'SLOWDOWN',
]);

const failureReasons = new Set([
  'FAILURE',
  'ADAPTIVE_FAILURE_BACKOFF',
  'ADAPTIVE_HARD_FAILURE_COOLDOWN',
  'ADAPTIVE_RECENT_FAILURES',
  'RETRY_AFTER_FAILURE',
  'RUNNING_STALE',
]);

const staleReasons = new Set(['STALE', 'RUNNING_STALE']);
const runningReasons = new Set(['RUNNING', 'RUNNING_STALE']);

const reasonTooltips = {
  ADAPTIVE_HIGH_CREATED_VOLUME: 'Created EMA is above the high-volume threshold, so this source is pulled forward.',
  ADAPTIVE_HIGH_UPDATED_VOLUME: 'Updated EMA is high, so the scheduler is checking this source sooner.',
  ADAPTIVE_LOW_VOLUME: 'Recent successful runs returned little or no data, so the interval was stretched.',
  ADAPTIVE_SCORE_COOLDOWN: 'The adaptive score fell below the cooldown threshold.',
  ADAPTIVE_SCORE_HIGH_ACTIVITY: 'The combined adaptive score is high enough to speed up the cadence.',
  ADAPTIVE_FAILURE_BACKOFF: 'Recent failures increased the retry interval.',
  ADAPTIVE_HARD_FAILURE_COOLDOWN: 'Failure rate crossed the hard cooldown threshold.',
  ADAPTIVE_RECENT_FAILURES: 'Recent failure signals are backing this source off.',
  RETRY_AFTER_FAILURE: 'The latest run failed, so the scheduler is retrying after a delay.',
  RUNNING: 'A run is already active; the scheduler is holding the lockout interval.',
  RUNNING_STALE: 'A running job exceeded its maximum duration and needs recovery.',
  SCHEDULED: 'Standard cadence from current freshness, activity, and reliability signals.',
  STALE: 'The source has not produced recent activity and is prioritized for refresh.',
  NO_DATA: 'No cached scheduler decision is available yet for this source.',
  UNKNOWN: 'The scheduler did not provide a decision reason.',
};

const reasonLabels = {
  ADAPTIVE_HIGH_CREATED_VOLUME: 'HIGH CREATED VOLUME',
  ADAPTIVE_HIGH_UPDATED_VOLUME: 'HIGH UPDATED VOLUME',
  ADAPTIVE_LOW_VOLUME: 'LOW VOLUME',
  ADAPTIVE_SCORE_COOLDOWN: 'SCORE COOLDOWN',
  ADAPTIVE_SCORE_HIGH_ACTIVITY: 'SCORE HIGH ACTIVITY',
  ADAPTIVE_FAILURE_BACKOFF: 'FAILURE BACKOFF',
  ADAPTIVE_HARD_FAILURE_COOLDOWN: 'HARD FAILURE COOLDOWN',
  ADAPTIVE_RECENT_FAILURES: 'RECENT FAILURES',
  RETRY_AFTER_FAILURE: 'RETRY AFTER FAILURE',
  RUNNING_STALE: 'RUNNING STALE',
  NO_DATA: 'NO DATA',
};

const toOptionalNumber = (value) => {
  if (value == null || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const toNumber = (value, fallback = 0) => {
  const number = toOptionalNumber(value);
  return number == null ? fallback : number;
};

const normalizeReason = (reason) => String(reason || 'UNKNOWN').trim().toUpperCase() || 'UNKNOWN';

const normalizeMetrics = (metrics) => ({
  ...emptyMetrics,
  created_avg: toNumber(metrics?.created_avg),
  updated_avg: toNumber(metrics?.updated_avg),
  failure_rate: toNumber(metrics?.failure_rate),
  zero_runs: toNumber(metrics?.zero_runs),
  freshness_lag: toOptionalNumber(metrics?.freshness_lag),
  created_per_run: toNumber(metrics?.created_per_run),
  trend: Array.isArray(metrics?.trend)
    ? metrics.trend.map((value) => toNumber(value)).filter((value) => Number.isFinite(value))
    : [],
  score: toOptionalNumber(metrics?.score),
  adaptive_raw_score: toOptionalNumber(metrics?.adaptive_raw_score),
});

export const normalizeDecision = (decision) => ({
  source: String(decision?.source || 'unknown'),
  reason: normalizeReason(decision?.reason),
  interval_seconds: decision?.interval_seconds == null ? null : toNumber(decision.interval_seconds),
  next_run_at: decision?.next_run_at || null,
  is_due: typeof decision?.is_due === 'boolean' ? decision.is_due : null,
  latest_run_status: decision?.latest_run_status || null,
  score_history: Array.isArray(decision?.score_history)
    ? decision.score_history.map((value) => toNumber(value)).filter((value) => Number.isFinite(value))
    : [],
  metrics: normalizeMetrics(decision?.metrics),
});

export const normalizeSchedulerState = (data) => (
  Array.isArray(data) ? data.map(normalizeDecision) : []
);

export const formatSourceName = (source) => (
  String(source || 'unknown')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
);

export const formatMetricNumber = (value) => {
  const number = toOptionalNumber(value);
  return number == null ? '-' : numberFormatter.format(number);
};

export const formatPercent = (value) => {
  const number = toOptionalNumber(value);
  return number == null ? '-' : `${percentFormatter.format(number * 100)}%`;
};

export const formatScore = (value) => {
  const number = toOptionalNumber(value);
  return number == null ? '--' : number.toFixed(2);
};

export const formatRawScore = (value) => {
  const number = toOptionalNumber(value);
  return number == null ? '--' : numberFormatter.format(number);
};

export const clampScore = (value) => {
  const number = toOptionalNumber(value);
  if (number == null) return 0;
  return Math.max(0, Math.min(number, 1));
};

export const formatDuration = (seconds) => {
  const totalSeconds = toOptionalNumber(seconds);
  if (totalSeconds == null || totalSeconds <= 0) return '-';
  if (totalSeconds < 60) return `${Math.round(totalSeconds)} sec`;

  const totalMinutes = Math.round(totalSeconds / 60);
  if (totalMinutes < 60) return `${totalMinutes} min`;

  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return minutes ? `${hours}h ${minutes}m` : `${hours}h`;
};

export const formatRelativeTime = (value) => {
  if (!value) return 'not scheduled';

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return 'not scheduled';

  const diffSeconds = Math.round((timestamp - Date.now()) / 1000);
  const absSeconds = Math.abs(diffSeconds);
  if (absSeconds < 30) return 'due now';

  const format = (amount, unit) => (
    diffSeconds > 0 ? `in ${amount} ${unit}` : `${amount} ${unit} ago`
  );

  const minutes = Math.round(absSeconds / 60);
  if (minutes < 60) return format(minutes, 'min');

  const hours = Math.round(minutes / 60);
  if (hours < 24) return format(hours, hours === 1 ? 'hour' : 'hours');

  const days = Math.round(hours / 24);
  return format(days, days === 1 ? 'day' : 'days');
};

export const getReasonMeta = (reason) => {
  const normalizedReason = normalizeReason(reason);

  return {
    label: reasonLabels[normalizedReason] || normalizedReason.replaceAll('_', ' '),
    tooltip: reasonTooltips[normalizedReason] || reasonTooltips.SCHEDULED,
    tone: failureReasons.has(normalizedReason)
      ? 'red'
      : staleReasons.has(normalizedReason)
        ? 'yellow'
        : highVolumeReasons.has(normalizedReason)
          ? 'green'
          : cooldownReasons.has(normalizedReason)
            ? 'red'
            : 'blue',
  };
};

export const getScoreMeta = (metrics) => {
  const score = toOptionalNumber(metrics?.score);

  if (score == null) {
    return {
      label: 'UNKNOWN',
      tone: 'neutral',
      description: 'Score is unavailable for this decision.',
    };
  }

  if (score >= 0.8) {
    return {
      label: 'HIGH PRIORITY',
      tone: 'green',
      description: 'Strong activity or freshness pressure is pulling this source forward.',
    };
  }

  if (score >= 0.4) {
    return {
      label: 'NORMAL',
      tone: 'blue',
      description: 'Signals are within the standard scheduling range.',
    };
  }

  return {
    label: 'LOW',
    tone: 'red',
    description: 'Low activity or failure pressure is reducing scheduling urgency.',
  };
};

export const getDecisionModeMeta = (decision) => {
  const reason = normalizeReason(decision?.reason);
  const latestRunStatus = normalizeReason(decision?.latest_run_status);

  if (runningReasons.has(reason) || latestRunStatus === 'RUNNING') {
    return { label: 'RUNNING', tone: 'blue' };
  }

  if (failureReasons.has(reason)) {
    return { label: 'ATTENTION', tone: 'red' };
  }

  if (cooldownReasons.has(reason)) {
    return { label: 'COOLDOWN', tone: 'red' };
  }

  if (reason === 'NO_DATA' || !decision?.next_run_at) {
    return { label: 'IDLE', tone: 'neutral' };
  }

  return { label: 'SCHEDULED', tone: 'blue' };
};

export const getDecisionBadges = (decision) => {
  const reason = normalizeReason(decision?.reason);
  const metrics = normalizeMetrics(decision?.metrics);
  const badges = [];

  if (highVolumeReasons.has(reason) || (metrics.score != null && metrics.score >= 0.8)) {
    badges.push({
      type: 'HIGH_VOLUME',
      label: 'HIGH_VOLUME',
      tone: 'green',
      tooltip: 'High activity signal: the scheduler should check this source sooner.',
    });
  }

  if (cooldownReasons.has(reason) || metrics.zero_runs >= 3) {
    badges.push({
      type: 'COOLDOWN',
      label: 'COOLDOWN',
      tone: 'red',
      tooltip: 'The interval is being stretched because current signals are weak or risky.',
    });
  }

  if (staleReasons.has(reason)) {
    badges.push({
      type: 'STALE',
      label: 'STALE',
      tone: 'yellow',
      tooltip: 'Freshness pressure is active because recent activity is missing or old.',
    });
  }

  if (failureReasons.has(reason) || metrics.failure_rate >= 0.25) {
    badges.push({
      type: 'FAILURE',
      label: 'FAILURE',
      tone: 'red',
      tooltip: 'Recent failures are affecting the scheduler decision.',
    });
  }

  if (!badges.length) {
    badges.push({
      type: 'STANDARD',
      label: 'STANDARD',
      tone: 'blue',
      tooltip: 'Standard decision from the latest activity and reliability metrics.',
    });
  }

  return badges;
};

export const getTrendMeta = (decision) => {
  const reason = normalizeReason(decision?.reason);
  const metrics = normalizeMetrics(decision?.metrics);
  const trend = metrics.trend;

  if (trend.length >= 2) {
    const first = trend[0];
    const last = trend[trend.length - 1];
    const delta = last - first;

    if (delta > 0) {
      return {
        direction: 'up',
        label: 'Created trend rising',
        tone: 'green',
        strength: Math.min(5, Math.max(1, Math.ceil(delta))),
      };
    }

    if (delta < 0) {
      return {
        direction: 'down',
        label: 'Created trend falling',
        tone: 'red',
        strength: Math.min(5, Math.max(1, Math.ceil(Math.abs(delta)))),
      };
    }
  }

  if (
    failureReasons.has(reason)
    || metrics.failure_rate >= 0.35
    || metrics.zero_runs >= 3
    || (metrics.score != null && metrics.score < 0.4)
  ) {
    return {
      direction: 'down',
      label: 'Decreasing activity',
      tone: 'red',
      strength: 1,
    };
  }

  if (
    highVolumeReasons.has(reason)
    || metrics.score >= 0.8
    || metrics.created_avg + metrics.updated_avg >= 10
  ) {
    return {
      direction: 'up',
      label: 'Increasing activity',
      tone: 'green',
      strength: 5,
    };
  }

  return {
    direction: 'flat',
    label: 'Stable activity',
    tone: 'blue',
    strength: 3,
  };
};

export const getSchedulerSummary = (decisions) => {
  const normalizedDecisions = Array.isArray(decisions) ? decisions : [];
  const nextRunTimestamps = normalizedDecisions
    .map((decision) => new Date(decision?.next_run_at).getTime())
    .filter((timestamp) => Number.isFinite(timestamp));

  return {
    sourceCount: normalizedDecisions.length,
    highPriorityCount: normalizedDecisions.filter(
      (decision) => getScoreMeta(decision?.metrics).label === 'HIGH PRIORITY'
    ).length,
    attentionCount: normalizedDecisions.filter((decision) => (
      getDecisionBadges(decision).some((badge) => ['COOLDOWN', 'FAILURE', 'STALE'].includes(badge.type))
    )).length,
    nextRunAt: nextRunTimestamps.length ? new Date(Math.min(...nextRunTimestamps)).toISOString() : null,
  };
};
