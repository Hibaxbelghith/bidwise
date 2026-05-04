const numberFormatter = new Intl.NumberFormat('en-US');

export const percentFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
});

export const statusStyles = {
  success: 'border-green-200 bg-green-50 text-green-700',
  failed: 'border-red-200 bg-red-50 text-red-700',
  skipped: 'border-yellow-200 bg-yellow-50 text-yellow-700',
  running: 'border-blue-200 bg-blue-50 text-blue-700',
  idle: 'border-neutral-200 bg-neutral-50 text-neutral-700',
  healthy: 'border-green-200 bg-green-50 text-green-700',
  degraded: 'border-yellow-200 bg-yellow-50 text-yellow-700',
};

export const severityStyles = {
  INFO: 'border-blue-200 bg-blue-50 text-blue-700',
  WARNING: 'border-yellow-200 bg-yellow-50 text-yellow-800',
  CRITICAL: 'border-red-200 bg-red-50 text-red-700',
};

export const formatNumber = (value) => numberFormatter.format(Number(value || 0));

export const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

export const getSystemStatus = (dashboard) => {
  const activeAlerts = dashboard?.monitoring?.alerts?.length || 0;
  const hasBacklog = Boolean(dashboard?.monitoring?.pipeline_lag?.backlog_detected);
  const workerStatus = dashboard?.celery?.status || 'degraded';
  const pipelineStatus = dashboard?.pipeline?.status || 'idle';

  if (activeAlerts > 0 || hasBacklog || workerStatus === 'degraded' || pipelineStatus === 'failed') {
    return {
      status: 'Attention needed',
      detail: 'Monitoring detected one or more items that need review.',
      iconTone: 'text-yellow-700 bg-yellow-100',
    };
  }

  if (pipelineStatus === 'running') {
    return {
      status: 'Pipeline running',
      detail: 'Ingestion is active and workers are available.',
      iconTone: 'text-blue-700 bg-blue-100',
    };
  }

  return {
    status: 'Healthy',
    detail: 'Sources, workers, and freshness checks are within expected ranges.',
    iconTone: 'text-green-700 bg-green-100',
  };
};
