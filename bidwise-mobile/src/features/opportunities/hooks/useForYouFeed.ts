import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { ProfileUser } from '@/src/features/profile/types';

import {
  listOpportunityRecommendations,
  listTenderRecommendations,
  type Opportunity,
  type Recommendation,
} from '../services/opportunitiesService';
import { getErrorMessage, wait } from '../utils/opportunityHelpers';
import {
  getProfileRecommendationTier,
  isCallsForTenderOnlyUser,
  isColdProfileRecommendationState,
  isQualifiedRecommendation,
  isStrongMatchRecommendation,
  recommendationToOpportunity,
  type ForYouProfileTier,
} from '../utils/recommendationUtils';

const DEFAULT_LIMIT = 20;
const MIN_LOADING_TIME_MS = 350;

type FetchMode = 'initial' | 'refresh';

export function useForYouFeed({
  ready,
  isAuthenticated,
  user,
  limit = DEFAULT_LIMIT,
}: {
  ready: boolean;
  isAuthenticated: boolean;
  user: ProfileUser | null;
  limit?: number;
}) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [hasLoaded, setHasLoaded] = useState(false);
  const fetchLockRef = useRef(false);
  const isTenderOnlyProfile = useMemo(() => isCallsForTenderOnlyUser(user), [user]);

  const profileTier = useMemo<ForYouProfileTier>(
    () => getProfileRecommendationTier(user),
    [user],
  );

  const fetchFeed = useCallback(
    async (mode: FetchMode) => {
      if (!ready || !isAuthenticated || fetchLockRef.current) return;

      fetchLockRef.current = true;
      if (mode === 'initial') setLoading(true);
      if (mode === 'refresh') setRefreshing(true);

      const startedAt = Date.now();

      try {
        const data = isTenderOnlyProfile
          ? await listTenderRecommendations({ limit: Math.max(limit, 50) })
          : await listOpportunityRecommendations({ limit });
        setRecommendations(Array.isArray(data) ? data.filter((item) => item?.id) : []);
        setError('');
      } catch (requestError) {
        setRecommendations([]);
        setError(getErrorMessage(requestError));
      } finally {
        const elapsed = Date.now() - startedAt;
        if (elapsed < MIN_LOADING_TIME_MS) {
          await wait(MIN_LOADING_TIME_MS - elapsed);
        }

        setHasLoaded(true);
        if (mode === 'initial') setLoading(false);
        if (mode === 'refresh') setRefreshing(false);
        fetchLockRef.current = false;
      }
    },
    [isAuthenticated, isTenderOnlyProfile, limit, ready],
  );

  useEffect(() => {
    if (!ready) return;

    if (!isAuthenticated) {
      setRecommendations([]);
      setError('');
      setLoading(false);
      setRefreshing(false);
      setHasLoaded(false);
      return;
    }

    if (!hasLoaded) {
      void fetchFeed('initial');
    }
  }, [fetchFeed, hasLoaded, isAuthenticated, ready]);

  const handleRefresh = useCallback(() => {
    if (!isAuthenticated) return;
    void fetchFeed('refresh');
  }, [fetchFeed, isAuthenticated]);

  const qualifiedRecommendations = useMemo(
    () => recommendations.filter((item) => isQualifiedRecommendation(item)),
    [recommendations],
  );

  const strongMatches = useMemo<Opportunity[]>(
    () =>
      qualifiedRecommendations
        .filter((item) => isStrongMatchRecommendation(item))
        .map(recommendationToOpportunity),
    [qualifiedRecommendations],
  );

  const relatedOpportunities = useMemo<Opportunity[]>(
    () =>
      qualifiedRecommendations
        .filter((item) => !isStrongMatchRecommendation(item))
        .map(recommendationToOpportunity),
    [qualifiedRecommendations],
  );

  const isColdProfile = useMemo(
    () => isColdProfileRecommendationState(user, qualifiedRecommendations),
    [qualifiedRecommendations, user],
  );

  return {
    recommendations,
    qualifiedRecommendations,
    strongMatches,
    relatedOpportunities,
    loading,
    refreshing,
    error,
    hasLoaded,
    profileTier,
    isColdProfile,
    isTenderOnlyProfile,
    handleRefresh,
  };
}

export default useForYouFeed;
