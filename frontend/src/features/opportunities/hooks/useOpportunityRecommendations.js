import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
  listOpportunityRecommendations,
  normalizeOpportunity,
} from '../services/opportunitiesService.js';
import { mergeRecommendationIntoOpportunity } from '../utils/recommendationUtils.js';

const DEFAULT_RECOMMENDATION_LIMIT = 20;
const RECOMMENDATION_STALE_TIME_MS = 2 * 60 * 1000;
const RECOMMENDATION_GC_TIME_MS = 10 * 60 * 1000;

const emptyRecommendations = [];
const emptyOpportunities = [];

const loadRecommendationDetails = async ({ recommendations }) =>
  recommendations.map((recommendation) =>
    mergeRecommendationIntoOpportunity(normalizeOpportunity(recommendation), recommendation),
  );


const recommendationToPreviewOpportunity = (recommendation) => {
  if (!recommendation?.id) return null;
  return {
    id: recommendation.id,
    titre: recommendation.title || recommendation.titre || '',
    organisation_nom: recommendation.company || '',
    ville: recommendation.location || '',
    type_opportunite: recommendation.type || '',
    skills: [],
    source: {},
    recommendation,
  };
};

export const useOpportunityRecommendations = ({
  enabled = true,
  includeDetails = false,
  limit = DEFAULT_RECOMMENDATION_LIMIT,
  cacheKey = 'default',
} = {}) => {
  const recommendationsQueryKey = useMemo(
    () => ['opportunity-recommendations', cacheKey, limit],
    [cacheKey, limit],
  );

  const recommendationsQuery = useQuery({
    queryKey: recommendationsQueryKey,
    queryFn: () => listOpportunityRecommendations({ limit }),
    enabled,
    staleTime: RECOMMENDATION_STALE_TIME_MS,
    gcTime: RECOMMENDATION_GC_TIME_MS,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const recommendations = recommendationsQuery.data || emptyRecommendations;
  const detailsQuery = useQuery({
    queryKey: ['opportunity-recommendation-details', cacheKey, recommendations.map((item) => item.id).join(',')],
    queryFn: () => loadRecommendationDetails({ recommendations }),
    enabled: enabled && includeDetails && recommendations.length > 0,
    staleTime: RECOMMENDATION_STALE_TIME_MS,
    gcTime: RECOMMENDATION_GC_TIME_MS,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const hydratedOpportunities = detailsQuery.data || emptyOpportunities;
  const hydratedById = useMemo(() => {
    const map = new Map();
    hydratedOpportunities.forEach((opportunity) => {
      if (opportunity?.id != null) {
        map.set(String(opportunity.id), opportunity);
      }
    });
    return map;
  }, [hydratedOpportunities]);
  const recommendedOpportunities = useMemo(
    () =>
      recommendations
        .map((recommendation) => (
          hydratedById.get(String(recommendation?.id)) ||
          recommendationToPreviewOpportunity(recommendation)
        ))
        .filter(Boolean),
    [hydratedById, recommendations],
  );

  const recommendationById = useMemo(() => {
    const map = new Map();
    recommendations.forEach((recommendation) => {
      if (recommendation?.id != null) {
        map.set(String(recommendation.id), recommendation);
      }
    });
    return map;
  }, [recommendations]);

  const refetch = useCallback(() => {
    recommendationsQuery.refetch();
    if (includeDetails) {
      detailsQuery.refetch();
    }
  }, [detailsQuery, includeDetails, recommendationsQuery]);

  return {
    recommendations,
    recommendationById,
    recommendedOpportunities,
    loading: enabled && recommendationsQuery.isLoading,
    isFetching: enabled && (recommendationsQuery.isFetching || detailsQuery.isFetching),
    isHydratingDetails: enabled && includeDetails && detailsQuery.isFetching && recommendations.length > 0,
    error:
      recommendationsQuery.error?.response?.data?.detail ||
      recommendationsQuery.error?.message ||
      detailsQuery.error?.response?.data?.detail ||
      detailsQuery.error?.message ||
      '',
    refetch,
  };
};

export default useOpportunityRecommendations;
