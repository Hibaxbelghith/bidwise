import { useEffect, useMemo, useState } from 'react';

import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import OpportunitiesBrowseSkeleton, {
  FetchingSkeletonBanner,
  SkeletonOpportunityCard,
} from '../browse/OpportunitiesBrowseSkeleton.jsx';
import OpportunityBrowseCard from '../browse/OpportunityBrowseCard.jsx';
import {
  getRecommendationScorePercent,
  getProfileCompletionScore,
  isFallbackRecommendation,
  isQualifiedRecommendation,
} from '../../utils/recommendationUtils.js';
import AiFeedCtaBlock from './AiFeedCtaBlock.jsx';
import ForYouEmptyState from './ForYouEmptyState.jsx';
import ForYouPreviewCard from './ForYouPreviewCard.jsx';
import OpportunitySplitDetailPanel from './OpportunitySplitDetailPanel.jsx';

const CURATED_FEED_LIMIT = 50;
const STRONG_MATCH_MIN_SCORE = 60;
const RELATED_REVIEW_MIN_SCORE = 35;

const filterQualifiedFeedItems = (items) =>
  (items || []).filter(
    (item) =>
      item?.recommendation &&
      isQualifiedRecommendation(item.recommendation, RELATED_REVIEW_MIN_SCORE),
  );

const getItemScorePercent = (item) =>
  getRecommendationScorePercent(item?.recommendation?.score ?? item?.recommendation?.match_score);

const getRecommendationBucket = (item) =>
  String(item?.recommendation?.recommendation_bucket || '').trim().toUpperCase();

const feedIdentity = (item) => {
  const id = String(item?.id || '').trim();
  if (id) return `id:${id}`;
  return [
    item?.titre,
    item?.organisation_nom,
    item?.ville,
    item?.contract_type,
  ]
    .map((value) => String(value || '').trim().toLowerCase())
    .join('|');
};

const dedupeFeedItems = (items = []) => {
  const seen = new Set();
  const unique = [];
  for (const item of items) {
    const key = feedIdentity(item);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    unique.push(item);
  }
  return unique;
};

const isResumeStillPreparing = (user) => {
  const resume = user?.profil?.active_resume;
  if (!resume) return false;
  const parsingStatus = String(resume.parsing_status || '').toUpperCase();
  const semanticStatus = String(resume.semantic_resume_status || '').toUpperCase();
  return (
    ['PENDING', 'PROCESSING'].includes(parsingStatus) ||
    (parsingStatus === 'SUCCEEDED' && ['PENDING', 'PROCESSING'].includes(semanticStatus))
  );
};

const ForYouResultsSkeleton = () => (
  <div className="grid gap-5 lg:grid-cols-[minmax(360px,420px)_minmax(0,1fr)] xl:grid-cols-[minmax(400px,460px)_minmax(0,1fr)]">
    <div className="space-y-4">
      {[0, 1, 2].map((index) => (
        <SkeletonOpportunityCard key={index} />
      ))}
    </div>
  </div>
);

const FeedSection = ({
  title,
  description,
  items,
  selectedOpportunity,
  isUserAuthenticated,
  onSelect,
}) => (
  <div className="space-y-3">
    <div className="px-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
        {title}
      </p>
      {description ? (
        <p className="mt-1 text-xs leading-5 text-neutral-500">{description}</p>
      ) : null}
    </div>
    {items.map((opportunity, index) => {
      const isSelected = String(opportunity?.id) === String(selectedOpportunity?.id);
      return (
        <div
          key={opportunity.id || `${title}-${index}`}
          className="rounded-md"
        >
          <div className="hidden lg:block">
            <ForYouPreviewCard
              opportunity={opportunity}
              isSelected={isSelected}
              isUserAuthenticated={isUserAuthenticated}
              onSelect={() => onSelect(opportunity?.id ?? null)}
            />
          </div>
          <div className="lg:hidden">
            <OpportunityBrowseCard
              opportunity={opportunity}
              isUserAuthenticated={isUserAuthenticated}
              showRecommendationInsights={Boolean(opportunity?.recommendation)}
              returnTab="for-you"
            />
          </div>
        </div>
      );
    })}
  </div>
);

const ForYouFeed = ({
  user,
  isUserAuthenticated,
  authLoading = false,
  profileRecommendationTier = 'insufficient',
  hasActiveFilters,
  recommendations = [],
  recommendedOpportunities,
  isTenderFeed = false,
  loading,
  showFetchingSpinner,
  error,
  onExploreMore,
  onResetFilters,
  onRetry,
}) => {
  const { t } = useLanguage();
  const feedItems = useMemo(() => {
    if (!isUserAuthenticated) return [];
    if (profileRecommendationTier === 'insufficient') return [];
    return filterQualifiedFeedItems(recommendedOpportunities);
  }, [
    isUserAuthenticated,
    profileRecommendationTier,
    recommendedOpportunities,
  ]);

  const visibleItems = useMemo(
    () => dedupeFeedItems(feedItems).slice(0, CURATED_FEED_LIMIT),
    [feedItems],
  );
  const strongMatchItems = useMemo(
    () =>
      visibleItems.filter((item) => {
        const bucket = getRecommendationBucket(item);
        if (bucket) return bucket === 'STRONG_MATCH';
        return (getItemScorePercent(item) ?? 0) >= STRONG_MATCH_MIN_SCORE;
      }),
    [visibleItems],
  );
  const relatedReviewItems = useMemo(
    () =>
      visibleItems.filter((item) => {
        const bucket = getRecommendationBucket(item);
        if (bucket) return bucket !== 'STRONG_MATCH';
        return (getItemScorePercent(item) ?? 0) < STRONG_MATCH_MIN_SCORE;
      }),
    [visibleItems],
  );
  const sectionedItems = useMemo(
    () => [...strongMatchItems, ...relatedReviewItems],
    [relatedReviewItems, strongMatchItems],
  );
  const [selectedOpportunityId, setSelectedOpportunityId] = useState(null);
  const selectedOpportunity = useMemo(() => {
    if (!sectionedItems.length) return null;
    return (
      sectionedItems.find((item) => String(item?.id) === String(selectedOpportunityId)) ||
      sectionedItems[0]
    );
  }, [selectedOpportunityId, sectionedItems]);
  const recommendedCount = feedItems.filter((item) => item?.recommendation).length;
  const profileCompletionScore = getProfileCompletionScore(user);
  const hasOnlyFallbackRecommendations =
    recommendations.length > 0 && recommendations.every((item) => isFallbackRecommendation(item));
  const resumeStillPreparing = isResumeStillPreparing(user);
  const showInitialLoading = loading && feedItems.length === 0;
  const showEmpty = !showInitialLoading && !error && feedItems.length === 0;
  const showError = !showInitialLoading && Boolean(error);
  const showPartialWarning = profileRecommendationTier === 'partial' && sectionedItems.length > 0;

  useEffect(() => {
    if (!sectionedItems.length) {
      setSelectedOpportunityId(null);
      return;
    }
    if (!sectionedItems.some((item) => String(item?.id) === String(selectedOpportunityId))) {
      setSelectedOpportunityId(sectionedItems[0]?.id ?? null);
    }
  }, [selectedOpportunityId, sectionedItems]);

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
        title={t('opportunities.profileNeedsSignal')}
        description={t('opportunities.profileNeedsSignalDesc')}
      />
    );
  }

  return (
    <section className="min-w-0">
      <div className="mb-4 rounded-md border border-neutral-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-neutral-950">
              {isTenderFeed ? t('opportunities.tenderFeed') : t('opportunities.aiFeed')}
            </p>
            <p className="mt-1 text-sm text-neutral-600">
              {isTenderFeed
                ? t('opportunities.tenderFeedDesc')
                : t('opportunities.aiFeedDesc')}
            </p>
          </div>
        </div>
      </div>

      {showPartialWarning ? (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">{t('opportunities.partialRecommendations')}</p>
          <p className="mt-1 leading-6">
            {t('opportunities.partialDesc', { score: profileCompletionScore })}
          </p>
        </div>
      ) : null}

      {showFetchingSpinner && sectionedItems.length > 0 ? <FetchingSkeletonBanner /> : null}

      {showInitialLoading ? <ForYouResultsSkeleton /> : null}

      {showError ? (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p>{error}</p>
            {onRetry ? (
              <Button type="button" variant="outline" onClick={onRetry}>
                {t('opportunities.retry')}
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
          title={
            hasOnlyFallbackRecommendations && resumeStillPreparing
              ? t('opportunities.matchesPreparing')
              : t('opportunities.noQualified')
          }
          description={
            hasOnlyFallbackRecommendations && resumeStillPreparing
              ? t('opportunities.preparingDesc')
              : t('opportunities.weakFilteredDesc')
          }
        />
      ) : null}

      {sectionedItems.length > 0 ? (
        <div className="grid gap-5 lg:grid-cols-[minmax(360px,420px)_minmax(0,1fr)] xl:grid-cols-[minmax(400px,460px)_minmax(0,1fr)]">
          <div className="space-y-3 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:pr-2">
            {strongMatchItems.length > 0 ? (
              <FeedSection
                title={isTenderFeed ? t('opportunities.strongPriorities') : t('opportunities.strongMatches')}
                description={
                  isTenderFeed
                    ? t('opportunities.strongTenderDesc')
                    : t('opportunities.strongMatchesDesc')
                }
                items={strongMatchItems}
                selectedOpportunity={selectedOpportunity}
                isUserAuthenticated={isUserAuthenticated}
                onSelect={setSelectedOpportunityId}
              />
            ) : null}
            {relatedReviewItems.length > 0 ? (
              <FeedSection
                title={
                  isTenderFeed
                    ? strongMatchItems.length > 0
                      ? t('opportunities.tendersMonitor')
                      : t('opportunities.tenderPriorities')
                    : strongMatchItems.length > 0
                      ? t('opportunities.relatedReview')
                      : t('opportunities.relatedOpportunities')
                }
                description={
                  isTenderFeed
                    ? strongMatchItems.length > 0
                      ? t('opportunities.tendersMonitorDesc')
                      : t('opportunities.tenderPrioritiesDesc')
                    : strongMatchItems.length > 0
                    ? t('opportunities.relatedReviewDesc')
                    : t('opportunities.relatedDesc')
                }
                items={relatedReviewItems}
                selectedOpportunity={selectedOpportunity}
                isUserAuthenticated={isUserAuthenticated}
                onSelect={setSelectedOpportunityId}
              />
            ) : null}
            <AiFeedCtaBlock onExploreMore={onExploreMore} />
          </div>

          <OpportunitySplitDetailPanel
            opportunity={selectedOpportunity}
            isUserAuthenticated={isUserAuthenticated}
          />
        </div>
      ) : null}
    </section>
  );
};

export default ForYouFeed;
