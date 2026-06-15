import { useCallback, useEffect, useMemo, useState } from 'react';

import { listenSavedOpportunityChanges } from '@/src/features/opportunities/utils/savedOpportunitiesStorage';

import {
  fetchMyApplications,
  fetchSavedOpportunities,
  withdrawMyApplication,
  type CandidateApplication,
} from '../services/dashboardService';

import type { Opportunity } from '@/src/features/opportunities/services/opportunitiesService';

const IN_PROGRESS_STATUSES = new Set([
  'SUBMITTED',
  'VIEWED_BY_ORGANIZATION',
  'SHORTLISTED',
  'EXTERNAL_CLICKED',
  'EXTERNAL_REMIND_LATER',
]);

export function useDashboardData(enabled: boolean) {
  const [savedItems, setSavedItems] = useState<Opportunity[]>([]);
  const [applications, setApplications] = useState<CandidateApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [withdrawingId, setWithdrawingId] = useState<number | null>(null);

  const loadData = useCallback(async (isRefresh = false) => {
    if (!enabled) {
      setSavedItems([]);
      setApplications([]);
      setLoading(false);
      setRefreshing(false);
      setError('');
      setNotice('');
      return;
    }

    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError('');
    setNotice('');

    const [savedResult, applicationsResult] = await Promise.allSettled([
      fetchSavedOpportunities(),
      fetchMyApplications(),
    ]);

    const savedFailed = savedResult.status === 'rejected';
    const applicationsFailed = applicationsResult.status === 'rejected';

    if (!savedFailed) {
      setSavedItems(savedResult.value);
    } else {
      setSavedItems([]);
    }

    if (!applicationsFailed) {
      setApplications(applicationsResult.value);
    } else {
      setApplications([]);
    }

    if (savedFailed && applicationsFailed) {
      setError('Unable to load your dashboard right now.');
    } else if (savedFailed) {
      setNotice('Saved opportunities are temporarily unavailable.');
    } else if (applicationsFailed) {
      setNotice('Applications are temporarily unavailable.');
    }

    setLoading(false);
    setRefreshing(false);
  }, [enabled]);

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  useEffect(() => {
    if (!enabled) return undefined;

    return listenSavedOpportunityChanges(() => {
      fetchSavedOpportunities()
        .then((items) => setSavedItems(items))
        .catch(() => {
          // Keep existing data if a refresh fails.
        });
    });
  }, [enabled]);

  const handleRefresh = useCallback(async () => {
    await loadData(true);
  }, [loadData]);

  const handleWithdraw = useCallback(async (applicationId: number) => {
    setWithdrawingId(applicationId);
    try {
      await withdrawMyApplication(applicationId);
      setApplications((current) =>
        current.map((item) =>
          item.id === applicationId
            ? { ...item, statut: 'WITHDRAWN' }
            : item,
        ),
      );
    } finally {
      setWithdrawingId(null);
    }
  }, []);

  const stats = useMemo(() => {
    const appliedCount = applications.length;
    const savedCount = savedItems.length;
    const inProgressCount = applications.filter((item) => IN_PROGRESS_STATUSES.has(item.statut)).length;

    return {
      appliedCount,
      savedCount,
      inProgressCount,
    };
  }, [applications, savedItems]);

  return {
    savedItems,
    applications,
    loading,
    refreshing,
    error,
    notice,
    withdrawingId,
    stats,
    handleRefresh,
    handleWithdraw,
  };
}
