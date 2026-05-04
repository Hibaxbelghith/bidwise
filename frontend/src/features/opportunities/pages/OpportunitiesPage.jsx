import { useMemo, useRef } from 'react';

import { useAuth } from '../../auth/AuthContext.jsx';
import OpportunitiesBrowseFilters from '../components/browse/OpportunitiesBrowseFilters.jsx';
import OpportunitiesBrowseHeader from '../components/browse/OpportunitiesBrowseHeader.jsx';
import OpportunitiesBrowseResults from '../components/browse/OpportunitiesBrowseResults.jsx';
import { DEFAULT_ORDERING } from '../constants/opportunityBrowse.js';
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

const getSourceName = (opportunity) => {
  const source = opportunity?.source;
  if (!source) return '';
  if (typeof source === 'string') return source;
  return source.nom || source.name || '';
};

const sortKeejobFirst = (items) =>
  [...items].sort((first, second) => {
    const firstIsKeejob = getSourceName(first).toLowerCase().includes('keejob');
    const secondIsKeejob = getSourceName(second).toLowerCase().includes('keejob');

    if (firstIsKeejob === secondIsKeejob) return 0;
    return firstIsKeejob ? -1 : 1;
  });

const OpportunitiesPage = () => {
  const resultsSectionRef = useRef(null);
  const { isAuthenticated, loading: authLoading } = useAuth();
  const {
    opportunities,
    cityOptions,
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
    ordering,
    setOrdering,
    setPage,
    resetFilters,
    refetch,
  } = useOpportunitiesBrowse();

  const isUserAuthenticated = !authLoading && isAuthenticated;
  const hasActiveFilters =
    Boolean(searchInput || typeFilter || statusFilter || cityFilter) || ordering !== DEFAULT_ORDERING;

  const countLabel = useMemo(() => {
    if (loading && opportunities.length === 0) return 'Loading opportunities...';
    if (count <= 0) return 'No opportunities found for current filters';
    return `${count} opportunities found`;
  }, [count, loading, opportunities.length]);
  const visiblePageNumbers = useMemo(
    () => getVisiblePageNumbers(page, totalPages),
    [page, totalPages]
  );
  const displayedOpportunities = useMemo(
    () => (page === 1 ? sortKeejobFirst(opportunities) : opportunities),
    [opportunities, page]
  );

  const scrollToResultsTop = () => {
    if (typeof window === 'undefined') return;

    if (resultsSectionRef.current) {
      resultsSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

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

  return (
    <div className="min-h-screen bg-neutral-50">
      <OpportunitiesBrowseHeader isUserAuthenticated={isUserAuthenticated} />

      <OpportunitiesBrowseFilters
        hasActiveFilters={hasActiveFilters}
        searchInput={searchInput}
        setSearchInput={setSearchInput}
        cityFilter={cityFilter}
        setCityFilter={setCityFilter}
        cityOptions={cityOptions}
        typeFilter={typeFilter}
        setTypeFilter={setTypeFilter}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        ordering={ordering}
        setOrdering={setOrdering}
        resetFilters={resetFilters}
      />

      <OpportunitiesBrowseResults
        resultsSectionRef={resultsSectionRef}
        countLabel={countLabel}
        page={page}
        totalPages={totalPages}
        showFetchingSpinner={showFetchingSpinner}
        loading={loading}
        isFetching={isFetching}
        error={error}
        opportunities={displayedOpportunities}
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
  );
};

export const OpportunitiesBrowse = OpportunitiesPage;
export default OpportunitiesPage;
