import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Button } from '../../../components/ui/button.jsx';
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
const OPPORTUNITY_TAB_STORAGE_KEY = 'bidwise:opportunities-active-tab:v1';
const RECOMMENDATION_ENGINE_VERSION = 'jobbert-hybrid-v2';
const VALID_TABS = new Set(['for-you', 'explore']);

const getInitialOpportunityTab = (location) => {
  const searchTab = new URLSearchParams(location.search).get('tab');
  if (VALID_TABS.has(searchTab)) return searchTab;

  if (typeof window !== 'undefined') {
    const storedTab = window.localStorage.getItem(OPPORTUNITY_TAB_STORAGE_KEY);
    if (VALID_TABS.has(storedTab)) return storedTab;
  }

  return 'explore';
};

const buildRecommendationCacheKey = (user) => {
  const profile = user?.profil || {};
  const activeResume = profile.active_resume || {};
  const profileSignals = {
    engine: RECOMMENDATION_ENGINE_VERSION,
    user: user?.id || user?.email || 'candidate',
    roles: profile.target_roles || [],
    skills: profile.competences || [],
    rawSkills: profile.raw_skills || [],
    normalizedSkills: profile.normalized_skills || [],
    sectors: profile.domaines_interet || profile.industries || profile.interests || [],
    locations: profile.preferred_locations || [],
    workModes: profile.work_mode_preferences || [],
    employmentTypes: profile.employment_types || [],
    experienceLevel: profile.niveau_experience || '',
    years: profile.annees_experience ?? '',
    resume: activeResume.id || activeResume.date_modification || '',
    resumeParsingStatus: activeResume.parsing_status || '',
    resumeSemanticStatus: activeResume.semantic_resume_status || '',
    resumeSemanticUpdated: activeResume.semantic_resume_updated_at || '',
    resumeSemanticVersion: activeResume.semantic_resume_version || '',
    updated: profile.date_modification || profile.updated_at || '',
  };

  return JSON.stringify(profileSignals);
};

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
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(() => getInitialOpportunityTab(location));
  const [pendingReturnPosition, setPendingReturnPosition] = useState(null);
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
  const showProfileCompletionPrompt =
    isUserAuthenticated && user?.profil?.onboarding_completed === false;
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
  const recommendationCacheKey = useMemo(() => buildRecommendationCacheKey(user), [user]);
  const recommendationsState = useOpportunityRecommendations({
    enabled: forYouEnabled,
    includeDetails: true,
    limit: 50,
    cacheKey: recommendationCacheKey,
  });
  const { refetch: refetchRecommendations } = recommendationsState;
  const effectiveTab = authLoading ? activeTab : isUserAuthenticated ? activeTab : 'explore';
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
  const forYouLoading = recommendationsState.loading;
  const forYouError = recommendationsState.error;
  const forYouShowFetchingSpinner = recommendationsState.isFetching || recommendationsState.isHydratingDetails;

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

  const setOpportunityTab = useCallback(
    (nextTab) => {
      const normalizedTab = VALID_TABS.has(nextTab) ? nextTab : 'explore';
      setActiveTab(normalizedTab);

      if (typeof window !== 'undefined') {
        window.localStorage.setItem(OPPORTUNITY_TAB_STORAGE_KEY, normalizedTab);
      }

      const params = new URLSearchParams(location.search);
      params.set('tab', normalizedTab);
      navigate(
        {
          pathname: location.pathname,
          search: `?${params.toString()}`,
        },
        { replace: true, state: location.state },
      );
    },
    [location.pathname, location.search, location.state, navigate],
  );

  useEffect(() => {
    const returnTab = location.state?.returnTab;
    if (returnTab === 'for-you' || returnTab === 'explore') {
      setOpportunityTab(returnTab);
    }

    if (returnTab === 'for-you' || returnTab === 'explore') {
      setPendingReturnPosition({
        tab: returnTab,
        opportunityId: location.state?.opportunityId ?? null,
        scrollY: Number(location.state?.scrollY),
      });
    }
  }, [location.state, setOpportunityTab]);

  useEffect(() => {
    if (!pendingReturnPosition || typeof window === 'undefined') return;
    if (pendingReturnPosition.tab !== effectiveTab) return;
    if (effectiveTab === 'for-you' && forYouLoading) return;
    if (effectiveTab === 'explore' && loading) return;

    window.requestAnimationFrame(() => {
      const opportunityId = pendingReturnPosition.opportunityId;
      const target = opportunityId
        ? document.getElementById(`opportunity-card-${opportunityId}`)
        : null;
      if (target) {
        target.scrollIntoView({ behavior: 'auto', block: 'center' });
      } else if (Number.isFinite(pendingReturnPosition.scrollY) && pendingReturnPosition.scrollY >= 0) {
        window.scrollTo({ top: pendingReturnPosition.scrollY, behavior: 'auto' });
      }
      setPendingReturnPosition(null);
    });
  }, [effectiveTab, forYouLoading, loading, pendingReturnPosition]);

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
  }, [refetchRecommendations]);

  const showForYouFeed = useCallback(() => {
    setOpportunityTab('for-you');
    scrollToResultsTopAfterFilter();
  }, [scrollToResultsTopAfterFilter, setOpportunityTab]);

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
      <OpportunitiesBrowseHeader
        isUserAuthenticated={isUserAuthenticated}
        authLoading={authLoading}
        user={user}
      />

      <OpportunitiesExperienceTabs
        activeTab={activeTab}
        isUserAuthenticated={isUserAuthenticated}
        onTabChange={setOpportunityTab}
      />

      {effectiveTab === 'explore' ? <OpportunitiesBrowseFilters {...filterProps} /> : null}

      {effectiveTab === 'for-you' ? (
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          

          <ForYouFeed
            user={user}
            isUserAuthenticated={isUserAuthenticated}
            authLoading={authLoading}
            profileRecommendationTier={profileRecommendationTier}
            hasActiveFilters={hasActiveFilters}
            recommendations={recommendationsState.recommendations}
            recommendedOpportunities={recommendationsState.recommendedOpportunities}
            loading={forYouLoading}
            showFetchingSpinner={forYouShowFetchingSpinner}
            error={forYouError}
            onResetFilters={resetFiltersAndScroll}
            onExploreMore={() => setOpportunityTab('explore')}
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
