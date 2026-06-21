import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
  listTenderRecommendations,
  listOpportunityRecommendations,
  normalizeOpportunity,
} from '../services/opportunitiesService.js';
import { mergeRecommendationIntoOpportunity } from '../utils/recommendationUtils.js';

const DEFAULT_RECOMMENDATION_LIMIT = 20;
const RECOMMENDATION_STALE_TIME_MS = 10 * 60 * 1000;
const RECOMMENDATION_GC_TIME_MS = 30 * 60 * 1000;

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
  recommendationType = 'job',
} = {}) => {
  const isTenderRecommendation = recommendationType === 'tender';
  const recommendationsQueryKey = useMemo(
    () => ['opportunities', 'recommendations', { cacheKey, limit, recommendationType }],
    [cacheKey, limit, recommendationType],
  );

  const recommendationsQuery = useQuery({
    queryKey: recommendationsQueryKey,
    queryFn: async () => {
      if (!isTenderRecommendation) {
        return listOpportunityRecommendations({ limit });
      }

      const payload = await listTenderRecommendations({ limit });
      return payload.results;
    },
    enabled: Boolean(enabled),
    staleTime: RECOMMENDATION_STALE_TIME_MS,
    gcTime: RECOMMENDATION_GC_TIME_MS,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const rawRecommendations = recommendationsQuery.data || emptyRecommendations;
  const recommendations = useMemo(
    () =>
      isTenderRecommendation
        ? rawRecommendations.map((item) => item?.recommendation).filter(Boolean)
        : rawRecommendations,
    [isTenderRecommendation, rawRecommendations],
  );
  const recommendationIds = useMemo(
    () => recommendations.map((item) => item.id).join(','),
    [recommendations],
  );
  const detailsQuery = useQuery({
    queryKey: ['opportunities', 'recommendation-details', { cacheKey, ids: recommendationIds }],
    queryFn: () => loadRecommendationDetails({ recommendations }),
    enabled: Boolean(enabled && includeDetails && !isTenderRecommendation && recommendations.length > 0),
    staleTime: RECOMMENDATION_STALE_TIME_MS,
    gcTime: RECOMMENDATION_GC_TIME_MS,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const hydratedOpportunities = isTenderRecommendation
    ? rawRecommendations
    : detailsQuery.data || emptyOpportunities;
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
    loading: Boolean(enabled && recommendationsQuery.isLoading),
    isFetching: Boolean(enabled && (recommendationsQuery.isFetching || detailsQuery.isFetching)),
    isHydratingDetails: Boolean(enabled && includeDetails && detailsQuery.isFetching && recommendations.length > 0),
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
