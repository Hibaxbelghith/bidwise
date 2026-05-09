import { useCallback, useMemo, useRef } from 'react';

import { useAuth } from '../../auth/AuthContext.jsx';
import OpportunitiesBrowseFilters from '../components/browse/OpportunitiesBrowseFilters.jsx';
import OpportunitiesBrowseHeader from '../components/browse/OpportunitiesBrowseHeader.jsx';
import OpportunitiesBrowseResults from '../components/browse/OpportunitiesBrowseResults.jsx';
import { useOpportunitiesBrowse } from '../hooks/useOpportunitiesBrowse.js';

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
  const { isAuthenticated, loading: authLoading } = useAuth();
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
      <OpportunitiesBrowseHeader isUserAuthenticated={isUserAuthenticated} />

      <OpportunitiesBrowseFilters {...filterProps} />

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
          opportunities={opportunities}
          isUserAuthenticated={isUserAuthenticated}
          hasPrevious={hasPrevious}
          hasNext={hasNext}
          visiblePageNumbers={visiblePageNumbers}
          onPageChange={handlePageChange}
          onPreviousPage={handlePreviousPage}
          onNextPage={handleNextPage}
          onResetFilters={resetFilters}
          onRetry={refetch}
        />
      </div>
    </div>
  );
};

export const OpportunitiesBrowse = OpportunitiesPage;
export default OpportunitiesPage;
