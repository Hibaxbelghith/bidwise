import { useEffect, useState } from 'react';

import { getDashboard } from '../services/adminService.js';

export const emptyDashboard = {
  kpis: {
    total_opportunities: 0,
    pipeline_activity_today: 0,
    sources_count: 0,
    change_rate: 0,
    run_success_rate: 0,
    success_rate: 0,
  },
  pipeline: {
    last_run: null,
    status: 'healthy',
    status_reason: '',
    status_detail: '',
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
  ai_supervision: {
    modules: {
      moderation: {
        module: 'Moderation AI',
        total: 0,
        processed: 0,
        coverage: 0,
        approved: 0,
        pending_review: 0,
        rejected: 0,
        skipped: 0,
        fallbacks: 0,
        admin_reviewed: 0,
        admin_overrides: 0,
        override_rate: 0,
        average_confidence: 0,
        top_category: '',
        provider: '',
        model: '',
        last_updated_at: null,
        current_issue: '',
      },
      opportunity_enrichment: {
        module: 'Opportunity Enrichment',
        total: 0,
        processed: 0,
        coverage: 0,
        applied_to_skills: 0,
        with_warnings: 0,
        average_confidence: 0,
        provider: '',
        model: '',
        last_updated_at: null,
        current_issue: '',
      },
      resume_semantic: {
        module: 'Resume Semantic AI',
        total: 0,
        processed: 0,
        coverage: 0,
        succeeded: 0,
        failed: 0,
        empty: 0,
        pending: 0,
        skipped: 0,
        average_confidence: 0,
        provider: '',
        model: '',
        last_updated_at: null,
        current_issue: '',
      },
      recommendation_readiness: {
        module: 'Recommendation Readiness',
        profile_total: 0,
        profile_embeddings: 0,
        profile_jobbert_embeddings: 0,
        profile_coverage: 0,
        opportunity_total: 0,
        opportunity_embeddings: 0,
        opportunity_pg_embeddings: 0,
        opportunity_jobbert_embeddings: 0,
        opportunity_coverage: 0,
        current_issue: '',
      },
    },
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
  ai_supervision: {
    ...emptyDashboard.ai_supervision,
    ...(data?.ai_supervision || {}),
    modules: {
      ...emptyDashboard.ai_supervision.modules,
      ...(data?.ai_supervision?.modules || {}),
      moderation: {
        ...emptyDashboard.ai_supervision.modules.moderation,
        ...(data?.ai_supervision?.modules?.moderation || {}),
      },
      opportunity_enrichment: {
        ...emptyDashboard.ai_supervision.modules.opportunity_enrichment,
        ...(data?.ai_supervision?.modules?.opportunity_enrichment || {}),
      },
      resume_semantic: {
        ...emptyDashboard.ai_supervision.modules.resume_semantic,
        ...(data?.ai_supervision?.modules?.resume_semantic || {}),
      },
      recommendation_readiness: {
        ...emptyDashboard.ai_supervision.modules.recommendation_readiness,
        ...(data?.ai_supervision?.modules?.recommendation_readiness || {}),
      },
    },
  },
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
