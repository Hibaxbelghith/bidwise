import { useMemo } from 'react';

import { Button } from '../../../../components/ui/button.jsx';
import OpportunitiesBrowseSkeleton, {
  FetchingSkeletonBanner,
} from '../browse/OpportunitiesBrowseSkeleton.jsx';
import OpportunityBrowseCard from '../browse/OpportunityBrowseCard.jsx';
import {
  getProfileCompletionScore,
  isQualifiedRecommendation,
  mergeRecommendationIntoOpportunity,
} from '../../utils/recommendationUtils.js';
import AiFeedCtaBlock from './AiFeedCtaBlock.jsx';
import ForYouEmptyState from './ForYouEmptyState.jsx';

const CURATED_FEED_LIMIT = 12;

const getRecommendationSortScore = (opportunity) => {
  const recommendation = opportunity?.recommendation;
  const score = Number(recommendation?.score ?? recommendation?.match_score ?? -1);
  return Number.isFinite(score) ? score : -1;
};

const sortFilteredFeed = (opportunities, recommendationById) =>
  (opportunities || [])
    .map((opportunity, index) => {
      const recommendation = recommendationById.get(String(opportunity?.id));
      return {
        opportunity: recommendation
          ? mergeRecommendationIntoOpportunity(opportunity, recommendation)
          : opportunity,
        index,
      };
    })
    .sort((left, right) => {
      const leftRecommended = Boolean(left.opportunity?.recommendation);
      const rightRecommended = Boolean(right.opportunity?.recommendation);

      if (leftRecommended !== rightRecommended) return leftRecommended ? -1 : 1;
      if (leftRecommended && rightRecommended) {
        return getRecommendationSortScore(right.opportunity) - getRecommendationSortScore(left.opportunity);
      }
      return left.index - right.index;
    })
    .map((item) => item.opportunity);

const filterQualifiedFeedItems = (items) =>
  (items || []).filter((item) => item?.recommendation && isQualifiedRecommendation(item.recommendation));

const ForYouFeed = ({
  user,
  isUserAuthenticated,
  authLoading = false,
  profileRecommendationTier = 'insufficient',
  hasActiveFilters,
  opportunities,
  recommendationById,
  recommendedOpportunities,
  loading,
  showFetchingSpinner,
  error,
  onExploreMore,
  onResetFilters,
  onRetry,
}) => {
  const feedItems = useMemo(() => {
    if (!isUserAuthenticated) return [];
    if (profileRecommendationTier === 'insufficient') return [];
    if (hasActiveFilters) {
      return filterQualifiedFeedItems(sortFilteredFeed(opportunities, recommendationById));
    }
    return filterQualifiedFeedItems(recommendedOpportunities);
  }, [
    hasActiveFilters,
    isUserAuthenticated,
    opportunities,
    profileRecommendationTier,
    recommendationById,
    recommendedOpportunities,
  ]);

  const visibleItems = feedItems.slice(0, CURATED_FEED_LIMIT);
  const recommendedCount = feedItems.filter((item) => item?.recommendation).length;
  const profileCompletionScore = getProfileCompletionScore(user);
  const showInitialLoading = loading && feedItems.length === 0;
  const showEmpty = !showInitialLoading && !error && feedItems.length === 0;
  const showError = !showInitialLoading && Boolean(error);
  const showPartialWarning = profileRecommendationTier === 'partial' && visibleItems.length > 0;

  if (authLoading) {
    return <OpportunitiesBrowseSkeleton />;
  }

  if (!isUserAuthenticated) {
    return (
      <ForYouEmptyState
        user={user}
        isUserAuthenticated={false}
        hasActiveFilters={hasActiveFilters}
        onResetFilters={onResetFilters}
      />
    );
  }

  if (profileRecommendationTier === 'insufficient') {
    return (
      <ForYouEmptyState
        user={user}
        isUserAuthenticated={isUserAuthenticated}
        hasActiveFilters={hasActiveFilters}
        onResetFilters={onResetFilters}
        title="Your profile needs more signal before For You can rank opportunities."
        description="Complete your profile to at least 40% so BidWise AI can recommend based on skills, target roles, and resume evidence instead of recency."
      />
    );
  }

  return (
    <section className="min-w-0">
      <div className="mb-4 rounded-md border border-neutral-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-neutral-950">
              {hasActiveFilters ? 'Personalized from current Explore filters' : 'Your AI recommendation feed'}
            </p>
            <p className="mt-1 text-sm text-neutral-600">
              {hasActiveFilters
                ? `${recommendedCount} recommended matches prioritized in this result set.`
                : 'Ranked by your resume, skills, preferred roles, and opportunity evidence.'}
            </p>
          </div>
          {hasActiveFilters ? (
            <Button type="button" variant="outline" onClick={onResetFilters}>
              Clear filters
            </Button>
          ) : null}
        </div>
      </div>

      {showPartialWarning ? (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Partial recommendations</p>
          <p className="mt-1 leading-6">
            Your profile is {profileCompletionScore}% complete, so these matches use the strongest
            available signals. Add more skills, target roles, or a resume to improve ranking quality.
          </p>
        </div>
      ) : null}

      {showFetchingSpinner && visibleItems.length > 0 ? <FetchingSkeletonBanner /> : null}

      {showInitialLoading ? <OpportunitiesBrowseSkeleton /> : null}

      {showError ? (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p>{error}</p>
            {onRetry ? (
              <Button type="button" variant="outline" onClick={onRetry}>
                Retry
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}

      {showEmpty ? (
        <ForYouEmptyState
          user={user}
          isUserAuthenticated={isUserAuthenticated}
          hasActiveFilters={hasActiveFilters}
          onResetFilters={onResetFilters}
          title="No strong matches yet."
          description="We filtered out weak or recency-only results. Add more profile details or check Explore while BidWise gathers stronger signals."
        />
      ) : null}

      {visibleItems.length > 0 ? (
        <div className="space-y-4">
          {visibleItems.map((opportunity, index) => (
            <div key={opportunity.id || index} className="space-y-4">
              <OpportunityBrowseCard
                opportunity={opportunity}
                isUserAuthenticated={isUserAuthenticated}
                showRecommendationInsights={Boolean(opportunity?.recommendation)}
              />
            </div>
          ))}
          <AiFeedCtaBlock onExploreMore={onExploreMore} />
        </div>
      ) : null}
    </section>
  );
};

export default ForYouFeed;
