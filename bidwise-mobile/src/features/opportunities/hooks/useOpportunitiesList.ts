import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { getOpportunities, type Opportunity } from '../services/opportunitiesService';
import { getErrorMessage, wait } from '../utils/opportunityHelpers';

const MIN_LOADING_TIME_MS = 400;
const PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 300;

export type OpportunityTypeFilter =
  | 'ALL'
  | 'EMPLOI'
  | 'STAGE'
  | 'SAISONNIER'
  | 'RECHERCHE'
  | 'PROJET'
  | 'FINANCEMENT';

type FetchMode = 'initial' | 'refresh' | 'more';

export function useOpportunitiesList({ ready }: { ready: boolean }) {
  const [searchInput, setSearchInput] = useState('');
  const [cityInput, setCityInput] = useState('');
  const [typeFilter, setTypeFilter] = useState<OpportunityTypeFilter>('ALL');

  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [debouncedCity, setDebouncedCity] = useState('');

  const [items, setItems] = useState<Opportunity[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);

  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const fetchLockRef = useRef(false);
  const hasLoadedRef = useRef(false);
  const hasNextRef = useRef(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setDebouncedCity(cityInput.trim());
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
    };
  }, [cityInput, searchInput]);

  const hasActiveFilters = useMemo(() => {
    return Boolean(searchInput.trim() || cityInput.trim() || typeFilter !== 'ALL');
  }, [cityInput, searchInput, typeFilter]);

  const fetchPage = useCallback(
    async (targetPage: number, mode: FetchMode) => {
      if (fetchLockRef.current) return;
      if (mode === 'more' && !hasNextRef.current) return;

      fetchLockRef.current = true;

      if (mode === 'initial') setInitialLoading(true);
      if (mode === 'refresh') setRefreshing(true);
      if (mode === 'more') setLoadingMore(true);

      const startedAt = Date.now();

      try {
        const data = await getOpportunities({
          page: targetPage,
          pageSize: PAGE_SIZE,
          search: debouncedSearch,
          city: debouncedCity,
          type: typeFilter === 'ALL' ? '' : typeFilter,
        });

        setItems((previousItems) => {
          if (targetPage === 1) return data.results;

          const knownIds = new Set(previousItems.map((entry) => entry.id));
          const nextItems = data.results.filter((entry) => !knownIds.has(entry.id));
          return [...previousItems, ...nextItems];
        });

        const nextAvailable = Boolean(data.next);
        setTotalCount(data.count);
        setPage(targetPage);
        setHasNext(nextAvailable);
        hasNextRef.current = nextAvailable;
        setError('');
        hasLoadedRef.current = true;
      } catch (requestError) {
        setError(getErrorMessage(requestError));
        if (targetPage === 1) {
          setItems([]);
          setHasNext(false);
          hasNextRef.current = false;
        }
      } finally {
        const elapsed = Date.now() - startedAt;
        if (elapsed < MIN_LOADING_TIME_MS) {
          await wait(MIN_LOADING_TIME_MS - elapsed);
        }

        if (mode === 'initial') setInitialLoading(false);
        if (mode === 'refresh') setRefreshing(false);
        if (mode === 'more') setLoadingMore(false);

        fetchLockRef.current = false;
      }
    },
    [debouncedCity, debouncedSearch, typeFilter],
  );

  useEffect(() => {
    if (!ready) return;

    const mode: FetchMode = hasLoadedRef.current ? 'refresh' : 'initial';
    void fetchPage(1, mode);
  }, [fetchPage, ready]);

  const handleRefresh = useCallback(() => {
    void fetchPage(1, 'refresh');
  }, [fetchPage]);

  const handleLoadMore = useCallback(() => {
    if (initialLoading || refreshing || loadingMore || !hasNext) return;
    void fetchPage(page + 1, 'more');
  }, [fetchPage, hasNext, initialLoading, loadingMore, page, refreshing]);

  const clearFilters = useCallback(() => {
    setSearchInput('');
    setCityInput('');
    setTypeFilter('ALL');
  }, []);

  return {
    items,
    totalCount,
    initialLoading,
    loadingMore,
    refreshing,
    error,
    searchInput,
    setSearchInput,
    cityInput,
    setCityInput,
    typeFilter,
    setTypeFilter,
    hasActiveFilters,
    clearFilters,
    handleRefresh,
    handleLoadMore,
  };
}

export default useOpportunitiesList;
