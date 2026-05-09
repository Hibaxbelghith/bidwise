import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles, Wand2 } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import OpportunitiesBrowseSkeleton, {
  FetchingSkeletonBanner,
} from './OpportunitiesBrowseSkeleton.jsx';
import OpportunityBrowseCard from './OpportunityBrowseCard.jsx';

const GuestAiTeaserCard = () => (
  <article className="overflow-hidden rounded-md border border-blue-200 bg-white shadow-sm">
    <div className="grid gap-0 md:grid-cols-[minmax(0,1fr)_280px]">
      <div className="p-5">
        <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-700">
          <Sparkles className="h-4 w-4" />
          AI Match preview
        </p>
        <h2 className="mt-2 text-lg font-semibold text-neutral-950">
          BidWise uses AI to rank fit, explain why, and assist your application.
        </h2>
        <p className="mt-2 text-sm leading-6 text-neutral-700">
          Create a free profile to unlock matching signals, similar opportunities, saved jobs,
          and a smarter application workflow.
        </p>
        <Button asChild className="mt-4 bg-blue-600 text-white hover:bg-blue-700">
          <Link to="/login">
            Create profile to unlock matching
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>
      <div className="border-t border-blue-100 bg-blue-50 p-5 md:border-l md:border-t-0">
        <div className="rounded-md border border-white bg-white/80 p-4 shadow-sm">
          <p className="inline-flex items-center gap-2 text-xs font-semibold text-neutral-900">
            <Wand2 className="h-4 w-4 text-blue-700" />
            AI opportunity insights
          </p>
          <div className="mt-3 space-y-2 text-sm font-medium text-neutral-800">
            <p>Python skill detected</p>
            <p>Backend engineering role</p>
            <p>Remote-friendly opportunity</p>
            <div className="relative overflow-hidden rounded-md border border-neutral-200 bg-white p-3">
              <div className="space-y-2 blur-sm">
                <p>Application angle matched to your profile</p>
                <p>Similar roles ranked by fit</p>
                <p>Suggested next action workflow</p>
              </div>
              <div className="absolute inset-0 bg-white/45" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </article>
);

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
  visiblePageNumbers,
  onPageChange,
  onPreviousPage,
  onNextPage,
  onResetFilters,
  onRetry,
}) => (
  <section ref={resultsSectionRef} className="min-w-0">
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
        {opportunities.map((opportunity, index) => (
          <div key={opportunity.id || index} className="space-y-4">
            <OpportunityBrowseCard
              opportunity={opportunity}
              isUserAuthenticated={isUserAuthenticated}
            />
            {!isUserAuthenticated && index === 3 ? <GuestAiTeaserCard /> : null}
          </div>
        ))}
      </div>
    ) : null}

    <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
      <Button
        variant="outline"
        onClick={onPreviousPage}
        disabled={!hasPrevious || loading || isFetching}
      >
        Previous
      </Button>
      {visiblePageNumbers[0] > 1 ? (
        <>
          <Button
            type="button"
            variant={page === 1 ? 'default' : 'outline'}
            className="min-w-10"
            disabled={loading || isFetching}
            aria-current={page === 1 ? 'page' : undefined}
            onClick={() => onPageChange(1)}
          >
            1
          </Button>
          {visiblePageNumbers[0] > 2 ? (
            <span className="px-1 text-sm text-neutral-400" aria-hidden="true">
              ...
            </span>
          ) : null}
        </>
      ) : null}
      {visiblePageNumbers.map((pageNumber) => (
        <Button
          key={pageNumber}
          type="button"
          variant={pageNumber === page ? 'default' : 'outline'}
          className="min-w-10"
          disabled={loading || isFetching}
          aria-current={pageNumber === page ? 'page' : undefined}
          onClick={() => onPageChange(pageNumber)}
        >
          {pageNumber}
        </Button>
      ))}
      {visiblePageNumbers[visiblePageNumbers.length - 1] < totalPages ? (
        <>
          {visiblePageNumbers[visiblePageNumbers.length - 1] < totalPages - 1 ? (
            <span className="px-1 text-sm text-neutral-400" aria-hidden="true">
              ...
            </span>
          ) : null}
          <Button
            type="button"
            variant={page === totalPages ? 'default' : 'outline'}
            className="min-w-10"
            disabled={loading || isFetching}
            aria-current={page === totalPages ? 'page' : undefined}
            onClick={() => onPageChange(totalPages)}
          >
            {totalPages}
          </Button>
        </>
      ) : null}
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
