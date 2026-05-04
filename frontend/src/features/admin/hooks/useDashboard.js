import { useEffect, useState } from 'react';

import { getDashboard } from '../services/adminService.js';

export const emptyDashboard = {
  kpis: {
    total_opportunities: 0,
    pipeline_activity_today: 0,
    sources_count: 0,
    success_rate: 0,
  },
  pipeline: {
    last_run: null,
    status: 'idle',
    processed: 0,
    created: 0,
    updated: 0,
  },
  sources: [],
  celery: {
    workers: 0,
    active_tasks: 0,
    scheduled_tasks: 0,
    reserved_tasks: 0,
    queue_length: 0,
    status: 'degraded',
  },
  monitoring: {
    embeddings: {
      total: 0,
      with_embeddings: 0,
      with_pg_embeddings: 0,
      missing_embeddings: 0,
      coverage: 0,
      is_complete: false,
    },
    logos: {
      total: 0,
      with_logo: 0,
      missing_or_placeholder: 0,
      coverage: 0,
    },
    pipeline_lag: {
      new_raw_remaining: 0,
      raw_total: 0,
      raw_status_counts: {},
      backlog_detected: false,
    },
    alerts: [],
    sources: [],
    queue: {},
  },
};

const normalizeDashboard = (data) => ({
  ...emptyDashboard,
  ...data,
  kpis: { ...emptyDashboard.kpis, ...(data?.kpis || {}) },
  pipeline: { ...emptyDashboard.pipeline, ...(data?.pipeline || {}) },
  celery: { ...emptyDashboard.celery, ...(data?.celery || {}) },
  sources: Array.isArray(data?.sources) ? data.sources : [],
  monitoring: {
    ...emptyDashboard.monitoring,
    ...(data?.monitoring || {}),
    embeddings: {
      ...emptyDashboard.monitoring.embeddings,
      ...(data?.monitoring?.embeddings || {}),
    },
    logos: {
      ...emptyDashboard.monitoring.logos,
      ...(data?.monitoring?.logos || {}),
    },
    pipeline_lag: {
      ...emptyDashboard.monitoring.pipeline_lag,
      ...(data?.monitoring?.pipeline_lag || {}),
    },
    sources: Array.isArray(data?.monitoring?.sources) ? data.monitoring.sources : [],
    alerts: Array.isArray(data?.monitoring?.alerts) ? data.monitoring.alerts : [],
  },
});

export const useDashboard = () => {
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadDashboard = async () => {
      try {
        setIsLoading(true);
        setError('');
        const { data } = await getDashboard();
        if (isMounted) {
          setDashboard(normalizeDashboard(data));
        }
      } catch (requestError) {
        if (isMounted) {
          setError(requestError.response?.data?.detail || 'Unable to load admin dashboard.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadDashboard();

    return () => {
      isMounted = false;
    };
  }, []);

  return {
    dashboard,
    isLoading,
    error,
  };
};
