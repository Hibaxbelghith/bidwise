import { useEffect, useRef, useState } from 'react';

import {
  approveOrganizationOpportunity,
  deleteOpportunity,
  getOpportunities,
  getSources,
  rejectOrganizationOpportunity,
} from '../services/adminService.js';
import { useDebouncedValue } from './useDebounce.js';
import { usePagination } from './usePagination.js';

const SEARCH_DEBOUNCE_MS = 350;
const INITIAL_LOADING_MIN_MS = 900;
const REFRESH_LOADING_MIN_MS = 500;

const normalizeSources = (data) => {
  const sourceItems = Array.isArray(data)
    ? data
    : Array.isArray(data?.results)
      ? data.results
      : [];

  const seenIds = new Set();
  return sourceItems.filter((item) => {
    const id = item?.id;
    const name = item?.nom;
    if (id == null || !name || seenIds.has(id)) return false;
    const normalizedName = String(name).toLowerCase();
    if (normalizedName.includes('benchmark')) return false;
    if (normalizedName.includes('recommendation')) return false;
    seenIds.add(id);
    return true;
  });
};

const normalizePaginatedResponse = (data) => {
  if (Array.isArray(data)) {
    return {
      results: data,
      count: data.length,
      next: null,
      previous: null,
    };
  }

  return {
    results: Array.isArray(data?.results) ? data.results : [],
    count: Number(data?.count || 0),
    next: data?.next || null,
    previous: data?.previous || null,
  };
};

const isRequestCanceled = (error) => error?.code === 'ERR_CANCELED';

const delay = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms);
});

export const useOpportunities = () => {
  const [opportunities, setOpportunities] = useState([]);
  const [sources, setSources] = useState([]);
  const [searchDraft, setSearchDraft] = useState('');
  const [source, setSource] = useState('');
  const [ordering, setOrdering] = useState('-created_at');
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSourcesLoading, setIsSourcesLoading] = useState(true);
  const [error, setError] = useState('');
  const [sourcesError, setSourcesError] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const [moderatingId, setModeratingId] = useState(null);
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const latestOpportunitiesRequest = useRef(0);
  const sectionRef = useRef(null);
  const debouncedSearch = useDebouncedValue(searchDraft.trim(), SEARCH_DEBOUNCE_MS);
  const { totalPages, pageRangeLabel, visiblePageNumbers } = usePagination({
    page,
    count,
    currentPageSize: opportunities.length,
  });

  const isInitialLoading = isLoading && !hasLoadedOnce;
  const isRefreshing = isLoading && hasLoadedOnce;

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, ordering, source]);

  useEffect(() => {
    const controller = new AbortController();
    const requestId = latestOpportunitiesRequest.current + 1;
    latestOpportunitiesRequest.current = requestId;
    const startTime = Date.now();
    const minimumLoadingMs = hasLoadedOnce
      ? REFRESH_LOADING_MIN_MS
      : INITIAL_LOADING_MIN_MS;

    const loadOpportunities = async () => {
      try {
        setIsLoading(true);
        setError('');

        const { data } = await getOpportunities({
          page,
          search: debouncedSearch,
          source,
          ordering,
          signal: controller.signal,
        });

        const elapsed = Date.now() - startTime;
        const remaining = minimumLoadingMs - elapsed;

        if (remaining > 0) {
          await delay(remaining);
        }

        if (latestOpportunitiesRequest.current !== requestId) return;

        const normalized = normalizePaginatedResponse(data);
        setOpportunities(normalized.results);
        setCount(normalized.count);
        setHasNext(Boolean(normalized.next));
        setHasPrevious(Boolean(normalized.previous));
        setHasLoadedOnce(true);
      } catch (err) {
        if (isRequestCanceled(err)) return;

        const elapsed = Date.now() - startTime;
        const remaining = minimumLoadingMs - elapsed;

        if (remaining > 0) {
          await delay(remaining);
        }

        if (latestOpportunitiesRequest.current !== requestId) return;

        setError(err.response?.data?.detail || 'Unable to load opportunities.');
        setOpportunities([]);
        setCount(0);
        setHasNext(false);
        setHasPrevious(false);
        setHasLoadedOnce(true);
      } finally {
        if (latestOpportunitiesRequest.current === requestId) {
          setIsLoading(false);
        }
      }
    };

    loadOpportunities();

    return () => controller.abort();
  }, [debouncedSearch, ordering, page, reloadKey, source]);

  useEffect(() => {
    const controller = new AbortController();
    const requestStartedAt = Date.now();

    const loadSources = async () => {
      try {
        setIsSourcesLoading(true);
        setSourcesError('');
        const { data } = await getSources({
          signal: controller.signal,
        });
        const remainingLoadingMs = REFRESH_LOADING_MIN_MS - (Date.now() - requestStartedAt);
        if (remainingLoadingMs > 0) {
          await delay(remainingLoadingMs);
        }
        setSources(normalizeSources(data));
      } catch (requestError) {
        if (isRequestCanceled(requestError)) return;
        const remainingLoadingMs = REFRESH_LOADING_MIN_MS - (Date.now() - requestStartedAt);
        if (remainingLoadingMs > 0) {
          await delay(remainingLoadingMs);
        }
        setSources([]);
        setSourcesError(requestError.response?.data?.detail || 'Unable to load sources.');
      } finally {
        setIsSourcesLoading(false);
      }
    };

    loadSources();

    return () => {
      controller.abort();
    };
  }, []);

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    setPage(1);
  };

  const handleSourceChange = (value) => {
    setPage(1);
    setSource(value);
  };

  const handleToggleOrdering = (field) => {
    const asc = field;
    const desc = `-${field}`;
    setOrdering((currentOrdering) => {
      if (currentOrdering === asc) return desc;
      if (currentOrdering === desc) return '';
      return asc;
    });
    setPage(1);
  };

  const handleDelete = async (opportunity) => {
    const confirmed = window.confirm(`Delete "${opportunity.title}"?`);
    if (!confirmed) return;

    try {
      setDeletingId(opportunity.id);
      await deleteOpportunity(opportunity.id);
      if (opportunities.length === 1 && page > 1) {
        setPage((currentPage) => currentPage - 1);
      } else {
        setReloadKey((currentKey) => currentKey + 1);
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to delete opportunity.');
    } finally {
      setDeletingId(null);
    }
  };

  const updateOpportunityInState = (updatedOpportunity) => {
    if (!updatedOpportunity?.id) return;
    setOpportunities((items) => (
      items.map((item) => (item.id === updatedOpportunity.id ? updatedOpportunity : item))
    ));
    setSelectedOpportunity((current) => (
      current?.id === updatedOpportunity.id ? updatedOpportunity : current
    ));
  };

  const handleApprove = async (opportunity) => {
    const note = window.prompt(`Approve "${opportunity.title}"? Optional note:`, '') ?? null;
    if (note === null) return;

    try {
      setModeratingId(opportunity.id);
      setError('');
      const { data } = await approveOrganizationOpportunity(opportunity.id, note);
      updateOpportunityInState(data?.opportunity);
      setReloadKey((currentKey) => currentKey + 1);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to approve opportunity.');
    } finally {
      setModeratingId(null);
    }
  };

  const handleReject = async (opportunity) => {
    const note = window.prompt(`Reject "${opportunity.title}"? Optional note:`, '') ?? null;
    if (note === null) return;

    try {
      setModeratingId(opportunity.id);
      setError('');
      const { data } = await rejectOrganizationOpportunity(opportunity.id, note);
      updateOpportunityInState(data?.opportunity);
      setReloadKey((currentKey) => currentKey + 1);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to reject opportunity.');
    } finally {
      setModeratingId(null);
    }
  };

  return {
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
  };
};
