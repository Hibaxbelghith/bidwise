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
  platform: {
    generated_at: null,
    users: {
      total: 0,
      active: 0,
      suspended: 0,
      admins: 0,
      candidates: 0,
      organizations: 0,
      new_today: 0,
      new_7_days: 0,
      new_30_days: 0,
    },
    applications: {
      total: 0,
      today: 0,
      last_7_days: 0,
      last_30_days: 0,
      by_status: {},
    },
    opportunities: {
      total: 0,
      active: 0,
      expired: 0,
      archived: 0,
      created_today: 0,
      created_7_days: 0,
      created_30_days: 0,
      by_type: {},
      by_status: {},
    },
    conversion: {
      application_rate: 0,
      applications_per_user: 0,
      applications_per_active_opportunity: 0,
    },
    growth: {
      days: 30,
      users: [],
      applications: [],
      opportunities: [],
    },
  },
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
  platform: {
    ...emptyDashboard.platform,
    ...(data?.platform || {}),
    users: { ...emptyDashboard.platform.users, ...(data?.platform?.users || {}) },
    applications: {
      ...emptyDashboard.platform.applications,
      ...(data?.platform?.applications || {}),
      by_status: data?.platform?.applications?.by_status || {},
    },
    opportunities: {
      ...emptyDashboard.platform.opportunities,
      ...(data?.platform?.opportunities || {}),
      by_type: data?.platform?.opportunities?.by_type || {},
      by_status: data?.platform?.opportunities?.by_status || {},
    },
    conversion: {
      ...emptyDashboard.platform.conversion,
      ...(data?.platform?.conversion || {}),
    },
    growth: {
      ...emptyDashboard.platform.growth,
      ...(data?.platform?.growth || {}),
      users: Array.isArray(data?.platform?.growth?.users) ? data.platform.growth.users : [],
      applications: Array.isArray(data?.platform?.growth?.applications) ? data.platform.growth.applications : [],
      opportunities: Array.isArray(data?.platform?.growth?.opportunities) ? data.platform.growth.opportunities : [],
    },
  },
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

export const useDashboard = (view = 'dashboard') => {
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadDashboard = async () => {
      try {
        setIsLoading(true);
        setError('');
        const requestView = view === 'dashboard' ? 'platform' : undefined;
        const { data } = await getDashboard({ view: requestView });
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
  }, [view]);

  return {
    dashboard,
    isLoading,
    error,
  };
};
