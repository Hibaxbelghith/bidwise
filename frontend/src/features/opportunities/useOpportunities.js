import { useEffect, useMemo, useState } from 'react';

import { listOpportunities } from './opportunitiesService';

const SEARCH_DEBOUNCE_MS = 400;
const DEFAULT_PAGE_SIZE = 20;

export const useOpportunities = () => {
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [ordering, setOrdering] = useState('-date_publication');
  const [page, setPage] = useState(1);

  const [count, setCount] = useState(0);
  const [opportunities, setOpportunities] = useState([]);
  const [next, setNext] = useState(null);
  const [previous, setPrevious] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timeoutId);
  }, [searchInput]);

  useEffect(() => {
    let isCancelled = false;

    const fetchData = async () => {
      try {
        setLoading(true);
        setError('');

        const data = await listOpportunities({
          search: debouncedSearch,
          type: typeFilter,
          status: statusFilter,
          ordering,
          page,
          pageSize: DEFAULT_PAGE_SIZE,
        });

        if (isCancelled) return;

        setCount(data.count ?? 0);
        setNext(data.next ?? null);
        setPrevious(data.previous ?? null);
        setOpportunities(data.results ?? []);
      } catch (err) {
        if (isCancelled) return;
        const message =
          err?.response?.data?.detail ||
          'Unable to load opportunities. Please try again.';
        setError(message);
        setOpportunities([]);
        setCount(0);
        setNext(null);
        setPrevious(null);
      } finally {
        if (!isCancelled) setLoading(false);
      }
    };

    fetchData();
    return () => {
      isCancelled = true;
    };
  }, [debouncedSearch, typeFilter, statusFilter, ordering, page, reloadToken]);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(count / DEFAULT_PAGE_SIZE)),
    [count]
  );

  const setTypeFilterAndResetPage = (value) => {
    setTypeFilter(value);
    setPage(1);
  };

  const setStatusFilterAndResetPage = (value) => {
    setStatusFilter(value);
    setPage(1);
  };

  const setOrderingAndResetPage = (value) => {
    setOrdering(value);
    setPage(1);
  };

  const refetch = () => setReloadToken((prev) => prev + 1);

  return {
    opportunities,
    count,
    next,
    previous,
    page,
    totalPages,
    hasNext: Boolean(next),
    hasPrevious: Boolean(previous),
    loading,
    error,
    searchInput,
    setSearchInput,
    typeFilter,
    setTypeFilter: setTypeFilterAndResetPage,
    statusFilter,
    setStatusFilter: setStatusFilterAndResetPage,
    ordering,
    setOrdering: setOrderingAndResetPage,
    setPage,
    refetch,
  };
};
