import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { useDebouncedValue } from './useDebounce.js';

export const PAGE_SIZE_OPTIONS = [20, 50, 100];
export const DEFAULT_PAGE_SIZE = 20;
const MAX_PAGE_SIZE = PAGE_SIZE_OPTIONS[PAGE_SIZE_OPTIONS.length - 1];
const SEARCH_DEBOUNCE_MS = 350;

const toPositiveInt = (value, fallback) => {
  const parsed = Number.parseInt(String(value || ''), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
};

export const useAdminUsersFilters = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = toPositiveInt(searchParams.get('page'), 1);
  const pageSize = Math.min(
    toPositiveInt(searchParams.get('page_size'), DEFAULT_PAGE_SIZE),
    MAX_PAGE_SIZE
  );

  const search = (searchParams.get('search') || '').trim();
  const role = (searchParams.get('role') || '').trim();
  const status = (searchParams.get('status') || '').trim();
  const provider = (searchParams.get('provider') || '').trim();
  const joinedAfter = searchParams.get('joined_after') || '';
  const joinedBefore = searchParams.get('joined_before') || '';
  const lastLoginAfter = searchParams.get('last_login_after') || '';
  const lastLoginBefore = searchParams.get('last_login_before') || '';
  const ordering = (searchParams.get('ordering') || '').trim();

  const [searchDraft, setSearchDraft] = useState(search);

  const debouncedSearch = useDebouncedValue(searchDraft.trim(), SEARCH_DEBOUNCE_MS);
  const suppressNextSearchSyncRef = useRef(false);
  const prevSearchRef = useRef(search);

  const updateQueryParams = useCallback((updates, { resetPage = false, replace = false } = {}) => {
    const next = new URLSearchParams(searchParams);

    Object.entries(updates).forEach(([key, value]) => {
      const normalized = value == null ? '' : String(value);
      if (!normalized) {
        next.delete(key);
      } else {
        next.set(key, normalized);
      }
    });

    if (resetPage) {
      next.set('page', '1');
    }

    setSearchParams(next, { replace });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (search !== prevSearchRef.current) {
      prevSearchRef.current = search;
      setSearchDraft(search);
      return;
    }

    if (debouncedSearch === search) return;

    if (suppressNextSearchSyncRef.current) {
      suppressNextSearchSyncRef.current = false;
      return;
    }

    updateQueryParams({ search: debouncedSearch }, { resetPage: true, replace: true });
  }, [debouncedSearch, search, updateQueryParams]);

  const resetFilters = useCallback(() => {
    suppressNextSearchSyncRef.current = true;
    setSearchDraft('');
    setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  const toggleOrdering = useCallback((field) => {
    const asc = field;
    const desc = `-${field}`;

    let nextOrdering = asc;
    if (ordering === asc) nextOrdering = desc;
    if (ordering === desc) nextOrdering = '';

    updateQueryParams({ ordering: nextOrdering }, { resetPage: true });
  }, [ordering, updateQueryParams]);

  const activeAdvancedFilters = [
    provider,
    joinedAfter,
    joinedBefore,
    lastLoginAfter,
    lastLoginBefore,
  ].filter(Boolean).length;

  return {
    page,
    pageSize,
    search,
    role,
    status,
    provider,
    joinedAfter,
    joinedBefore,
    lastLoginAfter,
    lastLoginBefore,
    ordering,
    searchDraft,
    setSearchDraft,
    updateQueryParams,
    resetFilters,
    toggleOrdering,
    activeAdvancedFilters,
  };
};
