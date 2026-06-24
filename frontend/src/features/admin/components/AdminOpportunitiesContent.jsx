import Filters from './opportunities/Filters.jsx';
import OpportunityModal from './opportunities/OpportunityModal.jsx';
import OpportunitiesTable from './opportunities/OpportunitiesTable.jsx';
import Pagination from './opportunities/Pagination.jsx';

const AdminOpportunitiesContent = ({
  opportunities,
  sources,
  searchDraft,
  source,
  ordering,
  page,
  count,
  hasNext,
  hasPrevious,
  isLoading,
  isSourcesLoading,
  error,
  sourcesError,
  deletingId,
  moderatingId,
  selectedOpportunity,
  sectionRef,
  totalPages,
  isInitialLoading,
  isRefreshing,
  pageRangeLabel,
  visiblePageNumbers,
  setSearchDraft,
  setPage,
  setSelectedOpportunity,
  handleSearchSubmit,
  handleSourceChange,
  handleToggleOrdering,
  handleDelete,
  handleApprove,
  handleReject,
}) => (
  <section ref={sectionRef} className="bg-neutral-50" aria-labelledby="admin-opportunities-heading">
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <Filters
        searchDraft={searchDraft}
        source={source}
        sources={sources}
        isLoading={isLoading}
        isSourcesLoading={isSourcesLoading}
        onSearchDraftChange={setSearchDraft}
        onSearchSubmit={handleSearchSubmit}
        onSourceChange={handleSourceChange}
      />

      {error || sourcesError ? (
        <div className="mb-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
          {error || sourcesError}
        </div>
      ) : null}

      <OpportunitiesTable
        opportunities={opportunities}
        count={count}
        isSourcesLoading={isSourcesLoading}
        isLoading={isLoading}
        isInitialLoading={isInitialLoading}
        isRefreshing={isRefreshing}
        ordering={ordering}
        deletingId={deletingId}
        onToggleOrdering={handleToggleOrdering}
        onViewOpportunity={setSelectedOpportunity}
        onDeleteOpportunity={handleDelete}
      />

      <Pagination
        page={page}
        count={count}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
        isLoading={isLoading}
        totalPages={totalPages}
        pageRangeLabel={pageRangeLabel}
        visiblePageNumbers={visiblePageNumbers}
        onPageChange={setPage}
      />
    </div>

    <OpportunityModal
      opportunity={selectedOpportunity}
      isModerating={moderatingId === selectedOpportunity?.id}
      onClose={() => setSelectedOpportunity(null)}
      onApprove={handleApprove}
      onReject={handleReject}
    />
  </section>
);

export default AdminOpportunitiesContent;
