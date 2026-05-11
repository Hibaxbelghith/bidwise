import { useCallback, useMemo, useRef, useState } from 'react';

import { useAuth } from '../../auth/AuthContext.jsx';
import OpportunitiesExperienceTabs from '../components/browse/OpportunitiesExperienceTabs.jsx';
import OpportunitiesBrowseFilters from '../components/browse/OpportunitiesBrowseFilters.jsx';
import OpportunitiesBrowseHeader from '../components/browse/OpportunitiesBrowseHeader.jsx';
import OpportunitiesBrowseResults from '../components/browse/OpportunitiesBrowseResults.jsx';
import ForYouFeed from '../components/recommendations/ForYouFeed.jsx';
import { useOpportunitiesBrowse } from '../hooks/useOpportunitiesBrowse.js';
import { useOpportunityRecommendations } from '../hooks/useOpportunityRecommendations.js';
import {
  canUseForYouFeed,
  getProfileRecommendationTier,
  isQualifiedRecommendation,
  mergeRecommendationIntoOpportunity,
} from '../utils/recommendationUtils.js';

const VISIBLE_PAGE_BUTTONS = 5;

const getVisiblePageNumbers = (currentPage, totalPages) => {
  if (totalPages <= VISIBLE_PAGE_BUTTONS) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const halfWindow = Math.floor(VISIBLE_PAGE_BUTTONS / 2);
  let start = Math.max(currentPage - halfWindow, 1);
  let end = start + VISIBLE_PAGE_BUTTONS - 1;

  if (end > totalPages) {
    end = totalPages;
    start = end - VISIBLE_PAGE_BUTTONS + 1;
  }

  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
};

const OpportunitiesPage = () => {
  const resultsSectionRef = useRef(null);
  const [activeTab, setActiveTab] = useState('explore');
  const { isAuthenticated, loading: authLoading, user } = useAuth();
  const {
    opportunities,
    cityOptions,
    sourceOptions,
    facets,
    count,
    page,
    totalPages,
    hasNext,
    hasPrevious,
    loading,
    isFetching,
    showFetchingSpinner,
    error,
    searchInput,
    setSearchInput,
    typeFilter,
    setTypeFilter,
    statusFilter,
    setStatusFilter,
    cityFilter,
    setCityFilter,
    sourceFilter,
    setSourceFilter,
    workModeFilter,
    setWorkModeFilter,
    experienceFilter,
    setExperienceFilter,
    setPage,
    resetFilters,
    refetch,
  } = useOpportunitiesBrowse();

  const isUserAuthenticated = !authLoading && isAuthenticated;
  const hasActiveFilters = Boolean(
    searchInput ||
      typeFilter ||
      statusFilter ||
      cityFilter ||
      sourceFilter ||
      workModeFilter ||
      experienceFilter
  );
  const forYouEnabled = isUserAuthenticated && canUseForYouFeed(user);
  const profileRecommendationTier = getProfileRecommendationTier(user);
  const recommendationsState = useOpportunityRecommendations({
    enabled: forYouEnabled,
    includeDetails: !hasActiveFilters,
    limit: 50,
    detailLimit: 20,
  });
  const { refetch: refetchRecommendations } = recommendationsState;
  const effectiveTab = isUserAuthenticated ? activeTab : 'explore';
  const opportunitiesWithRecommendations = useMemo(
    () =>
      opportunities.map((opportunity) => {
        const recommendation = recommendationsState.recommendationById.get(String(opportunity?.id));
        return isQualifiedRecommendation(recommendation)
          ? mergeRecommendationIntoOpportunity(opportunity, recommendation)
          : opportunity;
      }),
    [opportunities, recommendationsState.recommendationById],
  );

  const countLabel = useMemo(() => {
    if (loading && opportunities.length === 0) return 'Loading opportunities...';
    if (count <= 0) return 'No opportunities found for current filters';
    return `${count} opportunities found`;
  }, [count, loading, opportunities.length]);
  const visiblePageNumbers = useMemo(
    () => getVisiblePageNumbers(page, totalPages),
    [page, totalPages]
  );
  const scrollToResultsTop = useCallback(() => {
    if (typeof window === 'undefined') return;

    if (resultsSectionRef.current) {
      resultsSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const scrollToResultsTopAfterFilter = useCallback(() => {
    if (typeof window === 'undefined') return;

    window.requestAnimationFrame(() => {
      scrollToResultsTop();
    });
  }, [scrollToResultsTop]);

  const updateFilterAndScroll = useCallback(
    (setter) => (value) => {
      setter(value);
      scrollToResultsTopAfterFilter();
    },
    [scrollToResultsTopAfterFilter]
  );

  const resetFiltersAndScroll = useCallback(() => {
    resetFilters();
    scrollToResultsTopAfterFilter();
  }, [resetFilters, scrollToResultsTopAfterFilter]);

  const retryForYouFeed = useCallback(() => {
    refetchRecommendations();
    if (hasActiveFilters) {
      refetch();
    }
  }, [hasActiveFilters, refetch, refetchRecommendations]);

  const showForYouFeed = useCallback(() => {
    setActiveTab('for-you');
    scrollToResultsTopAfterFilter();
  }, [scrollToResultsTopAfterFilter]);

  const handlePreviousPage = () => {
    setPage((previousPage) => Math.max(1, previousPage - 1));
    scrollToResultsTop();
  };

  const handleNextPage = () => {
    setPage((previousPage) => previousPage + 1);
    scrollToResultsTop();
  };

  const handlePageChange = (nextPage) => {
    if (nextPage === page) return;
    setPage(nextPage);
    scrollToResultsTop();
  };

  const filterProps = {
    hasActiveFilters,
    searchInput,
    setSearchInput,
    cityFilter,
    setCityFilter: updateFilterAndScroll(setCityFilter),
    cityOptions,
    typeFilter,
    setTypeFilter: updateFilterAndScroll(setTypeFilter),
    statusFilter,
    setStatusFilter: updateFilterAndScroll(setStatusFilter),
    sourceFilter,
    setSourceFilter: updateFilterAndScroll(setSourceFilter),
    sourceOptions,
    facets,
    workModeFilter,
    setWorkModeFilter: updateFilterAndScroll(setWorkModeFilter),
    experienceFilter,
    setExperienceFilter: updateFilterAndScroll(setExperienceFilter),
    opportunities,
    resetFilters: resetFiltersAndScroll,
  };

  return (
    <div className="bidwise-browse-page min-h-screen bg-neutral-50">
      <OpportunitiesBrowseHeader isUserAuthenticated={isUserAuthenticated} user={user} />

      <OpportunitiesExperienceTabs
        activeTab={activeTab}
        isUserAuthenticated={isUserAuthenticated}
        onTabChange={setActiveTab}
      />

      {effectiveTab === 'explore' ? <OpportunitiesBrowseFilters {...filterProps} /> : null}

      {effectiveTab === 'for-you' ? (
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
          <ForYouFeed
            user={user}
            isUserAuthenticated={isUserAuthenticated}
            authLoading={authLoading}
            profileRecommendationTier={profileRecommendationTier}
            hasActiveFilters={hasActiveFilters}
            opportunities={opportunities}
            recommendationById={recommendationsState.recommendationById}
            recommendedOpportunities={recommendationsState.recommendedOpportunities}
            loading={hasActiveFilters ? loading : recommendationsState.loading}
            showFetchingSpinner={hasActiveFilters ? showFetchingSpinner : false}
            error={hasActiveFilters ? error || recommendationsState.error : recommendationsState.error}
            onResetFilters={resetFiltersAndScroll}
            onExploreMore={() => setActiveTab('explore')}
            onRetry={retryForYouFeed}
          />
        </div>
      ) : null}

      {effectiveTab === 'explore' ? (
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[300px_minmax(0,1fr)] lg:px-8">
          <OpportunitiesBrowseFilters {...filterProps} variant="sidebar" />

          <OpportunitiesBrowseResults
            resultsSectionRef={resultsSectionRef}
            countLabel={countLabel}
            page={page}
            totalPages={totalPages}
            showFetchingSpinner={showFetchingSpinner}
            loading={loading}
            isFetching={isFetching}
            error={error}
            opportunities={opportunitiesWithRecommendations}
            isUserAuthenticated={isUserAuthenticated}
            user={user}
            hasPrevious={hasPrevious}
            hasNext={hasNext}
            visiblePageNumbers={visiblePageNumbers}
            onPageChange={handlePageChange}
            onPreviousPage={handlePreviousPage}
            onNextPage={handleNextPage}
            onResetFilters={resetFiltersAndScroll}
            onRetry={refetch}
            onShowMatches={showForYouFeed}
          />
        </div>
      ) : null}
    </div>
  );
};

export const OpportunitiesBrowse = OpportunitiesPage;
export default OpportunitiesPage;
