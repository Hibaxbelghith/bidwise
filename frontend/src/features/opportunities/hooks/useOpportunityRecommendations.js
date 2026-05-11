import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getOpportunityById,
  listOpportunityRecommendations,
} from '../services/opportunitiesService.js';
import { mergeRecommendationIntoOpportunity } from '../utils/recommendationUtils.js';

const DEFAULT_RECOMMENDATION_LIMIT = 20;

export const useOpportunityRecommendations = ({
  enabled = true,
  includeDetails = false,
  limit = DEFAULT_RECOMMENDATION_LIMIT,
  detailLimit = limit,
} = {}) => {
  const [recommendations, setRecommendations] = useState([]);
  const [recommendedOpportunities, setRecommendedOpportunities] = useState([]);
  const [loading, setLoading] = useState(Boolean(enabled));
  const [isHydratingDetails, setIsHydratingDetails] = useState(false);
  const [error, setError] = useState('');
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let isCancelled = false;

    if (!enabled) {
      setRecommendations([]);
      setRecommendedOpportunities([]);
      setLoading(false);
      setIsHydratingDetails(false);
      setError('');
      return undefined;
    }

    const fetchRecommendations = async () => {
      try {
        setLoading(true);
        setError('');

        const data = await listOpportunityRecommendations({ limit });
        if (isCancelled) return;

        setRecommendations(data);

        if (!includeDetails || data.length === 0) {
          setRecommendedOpportunities([]);
          return;
        }

        setIsHydratingDetails(true);
        const detailRecommendations = data.slice(0, Math.max(1, Number(detailLimit) || limit));
        const settled = await Promise.allSettled(
          detailRecommendations.map((recommendation) => getOpportunityById(recommendation.id)),
        );
        if (isCancelled) return;

        const nextOpportunities = settled
          .map((result, index) => {
            if (result.status !== 'fulfilled' || !result.value) return null;
            return mergeRecommendationIntoOpportunity(result.value, detailRecommendations[index]);
          })
          .filter(Boolean);

        setRecommendedOpportunities(nextOpportunities);
      } catch (err) {
        if (isCancelled) return;
        const message =
          err?.response?.data?.detail ||
          'Unable to load AI recommendations right now.';
        setError(message);
        setRecommendations([]);
        setRecommendedOpportunities([]);
      } finally {
        if (!isCancelled) {
          setLoading(false);
          setIsHydratingDetails(false);
        }
      }
    };

    fetchRecommendations();
    return () => {
      isCancelled = true;
    };
  }, [detailLimit, enabled, includeDetails, limit, reloadToken]);

  const recommendationById = useMemo(() => {
    const map = new Map();
    recommendations.forEach((recommendation) => {
      if (recommendation?.id != null) {
        map.set(String(recommendation.id), recommendation);
      }
    });
    return map;
  }, [recommendations]);

  const refetch = useCallback(() => setReloadToken((value) => value + 1), []);

  return {
    recommendations,
    recommendationById,
    recommendedOpportunities,
    loading,
    isHydratingDetails,
    error,
    refetch,
  };
};

export default useOpportunityRecommendations;
