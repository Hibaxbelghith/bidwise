import { ChevronLeft, ChevronRight } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';

const Pagination = ({
  page,
  count,
  hasNext,
  hasPrevious,
  isLoading,
  totalPages,
  pageRangeLabel,
  visiblePageNumbers,
  onPageChange,
}) => (
  <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <p className="text-sm text-neutral-500">
      Showing {pageRangeLabel} of {count} opportunities
    </p>
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button
        type="button"
        variant="outline"
        disabled={!hasPrevious || isLoading}
        onClick={() => onPageChange((currentPage) => Math.max(currentPage - 1, 1))}
      >
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        Prev
      </Button>
      {visiblePageNumbers[0] > 1 ? (
        <>
          <Button
            type="button"
            variant={page === 1 ? 'default' : 'outline'}
            className="min-w-10"
            disabled={isLoading}
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
          disabled={isLoading}
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
            disabled={isLoading}
            onClick={() => onPageChange(totalPages)}
          >
            {totalPages}
          </Button>
        </>
      ) : null}
      <Button
        type="button"
        variant="outline"
        disabled={!hasNext || isLoading}
        onClick={() => onPageChange((currentPage) => currentPage + 1)}
      >
        Next
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    </div>
  </div>
);

export default Pagination;
