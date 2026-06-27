import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import OpportunitiesBrowseSkeleton, {
  FetchingSkeletonBanner,
} from './OpportunitiesBrowseSkeleton.jsx';
import OpportunityBrowseCard from './OpportunityBrowseCard.jsx';
import OpportunitiesBrowseInterruptionCard, {
  buildBrowseInterruptionCards,
} from './OpportunitiesBrowseInterruptionCards.jsx';

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
  user,
  hasPrevious,
  hasNext,
  visiblePageNumbers,
  onPageChange,
  onPreviousPage,
  onNextPage,
  onResetFilters,
  onRetry,
  onShowMatches,
}) => {
  const { t } = useLanguage();
  const interruptionCards = buildBrowseInterruptionCards({
    isUserAuthenticated,
    user,
    onShowMatches,
  });

  return (
    <section ref={resultsSectionRef} className="min-h-[60vh] min-w-0" aria-busy={loading || isFetching}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-neutral-700">{countLabel}</p>
        <p className="text-sm text-neutral-600">
          {t('opportunities.results.pageOf', { page, totalPages })}
        </p>
      </div>

      {showFetchingSpinner && opportunities.length > 0 ? <FetchingSkeletonBanner /> : null}

      {loading && opportunities.length === 0 ? <OpportunitiesBrowseSkeleton /> : null}

      {!loading && error && opportunities.length === 0 ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="mb-3">{error}</p>
          <Button variant="outline" onClick={onRetry}>
            {t('opportunities.retry')}
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
          <h2 className="mb-2 text-lg font-semibold text-neutral-900">{t('opportunities.results.noOpportunitiesFound')}</h2>
          <p className="text-neutral-600">{t('opportunities.results.adjustSearch')}</p>
          <div className="mt-4">
            <Button variant="outline" onClick={onResetFilters}>
              {t('opportunities.results.resetFilters')}
            </Button>
          </div>
        </div>
      ) : null}

      {!loading && opportunities.length > 0 ? (
        <div className="space-y-4">
          {opportunities.map((opportunity, index) => (
            <div
              key={opportunity.id || index}
              className="space-y-4 [content-visibility:auto] [contain-intrinsic-size:1px_260px]"
            >
              <OpportunityBrowseCard
                opportunity={opportunity}
                isUserAuthenticated={isUserAuthenticated}
              />
              {(index + 1) % 5 === 0 && interruptionCards.length > 0 ? (
                <OpportunitiesBrowseInterruptionCard
                  card={interruptionCards[Math.floor(index / 5) % interruptionCards.length]}
                />
              ) : null}
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
          {t('opportunities.results.previous')}
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
          {t('opportunities.results.next')}
        </Button>
      </div>
    </section>
  );
};

export default OpportunitiesBrowseResults;
