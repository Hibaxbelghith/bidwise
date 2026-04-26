import { useMemo, useRef } from 'react';

import { useAuth } from '../../auth/AuthContext.jsx';
import OpportunitiesBrowseFilters from '../components/browse/OpportunitiesBrowseFilters.jsx';
import OpportunitiesBrowseHeader from '../components/browse/OpportunitiesBrowseHeader.jsx';
import OpportunitiesBrowseResults from '../components/browse/OpportunitiesBrowseResults.jsx';
import { DEFAULT_ORDERING } from '../constants/opportunityBrowse.js';
import { useOpportunitiesBrowse } from '../hooks/useOpportunitiesBrowse.js';

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
        opportunities={opportunities}
        isUserAuthenticated={isUserAuthenticated}
        hasPrevious={hasPrevious}
        hasNext={hasNext}
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
