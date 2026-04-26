import { Button } from '../../../../components/ui/button.jsx';
import OpportunitiesBrowseSkeleton, {
  FetchingSkeletonBanner,
} from './OpportunitiesBrowseSkeleton.jsx';
import OpportunityBrowseCard from './OpportunityBrowseCard.jsx';

const OpportunitiesBrowseResults = ({
  resultsSectionRef,
  countLabel,
  page,
  totalPages,
  showFetchingSpinner,
  loading,
  isFetching,
  error,
  opportunities,
  isUserAuthenticated,
  hasPrevious,
  hasNext,
  onPreviousPage,
  onNextPage,
  onResetFilters,
  onRetry,
}) => (
  <section ref={resultsSectionRef} className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <p className="text-sm font-medium text-neutral-700">{countLabel}</p>
      <p className="text-sm text-neutral-600">
        Page {page} of {totalPages}
      </p>
    </div>

    {showFetchingSpinner && opportunities.length > 0 ? <FetchingSkeletonBanner /> : null}

    {loading && opportunities.length === 0 ? <OpportunitiesBrowseSkeleton /> : null}

    {!loading && error && opportunities.length === 0 ? (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
        <p className="mb-3">{error}</p>
        <Button variant="outline" onClick={onRetry}>
          Retry
        </Button>
      </div>
    ) : null}

    {!loading && error && opportunities.length > 0 ? (
      <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        {error}
      </div>
    ) : null}

    {!loading && !error && opportunities.length === 0 ? (
      <div className="rounded-xl border border-neutral-200 bg-white p-8 text-center shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-neutral-900">No opportunities found</h2>
        <p className="text-neutral-600">Try adjusting search terms or filters.</p>
        <div className="mt-4">
          <Button variant="outline" onClick={onResetFilters}>
            Reset filters
          </Button>
        </div>
      </div>
    ) : null}

    {!loading && opportunities.length > 0 ? (
      <div className="space-y-4">
        {opportunities.map((opportunity) => (
          <OpportunityBrowseCard
            key={opportunity.id}
            opportunity={opportunity}
            isUserAuthenticated={isUserAuthenticated}
          />
        ))}
      </div>
    ) : null}

    <div className="mt-6 flex items-center justify-center gap-3">
      <Button
        variant="outline"
        onClick={onPreviousPage}
        disabled={!hasPrevious || loading || isFetching}
      >
        Previous
      </Button>
      <span className="text-sm text-neutral-600">
        {page} / {totalPages}
      </span>
      <Button
        variant="outline"
        onClick={onNextPage}
        disabled={!hasNext || loading || isFetching}
      >
        Next
      </Button>
    </div>
  </section>
);

export default OpportunitiesBrowseResults;
