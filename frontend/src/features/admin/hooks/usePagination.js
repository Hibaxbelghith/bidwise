import { useMemo } from 'react';

export const PAGE_SIZE = 20;

const VISIBLE_PAGE_BUTTONS = 5;

export const getVisiblePageNumbers = (currentPage, totalPages) => {
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

export const usePagination = ({ page, count, currentPageSize, pageSize = PAGE_SIZE }) => {
  const totalPages = useMemo(() => Math.max(Math.ceil(count / pageSize), 1), [count, pageSize]);

  const pageRangeLabel = useMemo(() => {
    if (!count || !currentPageSize) return '0-0';
    const start = (page - 1) * pageSize + 1;
    const end = start + currentPageSize - 1;
    return `${start}-${end}`;
  }, [count, currentPageSize, page, pageSize]);

  const visiblePageNumbers = useMemo(
    () => getVisiblePageNumbers(page, totalPages),
    [page, totalPages]
  );

  return {
    totalPages,
    pageRangeLabel,
    visiblePageNumbers,
  };
};
