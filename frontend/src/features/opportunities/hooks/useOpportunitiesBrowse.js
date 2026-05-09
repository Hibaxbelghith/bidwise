import { useEffect, useMemo, useRef, useState } from 'react';

import {
  DEFAULT_BROWSE_STATE,
  DEFAULT_SORT,
  DEFAULT_PAGE_SIZE,
  FETCHING_SKELETON_DELAY_MS,
  FETCHING_SKELETON_MIN_VISIBLE_MS,
  FILTERS_STORAGE_KEY,
  SEARCH_DEBOUNCE_MS,
} from '../constants/opportunityBrowse.js';
import { listOpportunities, listOpportunitySources } from '../services/opportunitiesService.js';

const readPersistedBrowseState = () => {
  if (typeof window === 'undefined') return DEFAULT_BROWSE_STATE;

  try {
    const raw = window.sessionStorage.getItem(FILTERS_STORAGE_KEY);
    if (!raw) return DEFAULT_BROWSE_STATE;

    const parsed = JSON.parse(raw);
    const page = Number.parseInt(parsed?.page, 10);
    return {
      searchInput: String(parsed?.searchInput || ''),
      typeFilter: String(parsed?.typeFilter || ''),
      statusFilter: String(parsed?.statusFilter || ''),
      cityFilter: String(parsed?.cityFilter || ''),
      sourceFilter: String(parsed?.sourceFilter || ''),
      workModeFilter: String(parsed?.workModeFilter || ''),
      experienceFilter: String(parsed?.experienceFilter || ''),
      page: Number.isFinite(page) && page > 0 ? page : 1,
    };
  } catch {
    return DEFAULT_BROWSE_STATE;
  }
};

export const useOpportunitiesBrowse = () => {
  const [initialState] = useState(() => readPersistedBrowseState());
  const [searchInput, setSearchInput] = useState(initialState.searchInput);
  const [debouncedSearch, setDebouncedSearch] = useState(initialState.searchInput.trim());
  const [typeFilter, setTypeFilter] = useState(initialState.typeFilter);
  const [statusFilter, setStatusFilter] = useState(initialState.statusFilter);
  const [cityFilter, setCityFilter] = useState(initialState.cityFilter);
  const [sourceFilter, setSourceFilter] = useState(initialState.sourceFilter);
  const [workModeFilter, setWorkModeFilter] = useState(initialState.workModeFilter);
  const [experienceFilter, setExperienceFilter] = useState(initialState.experienceFilter);
  const [page, setPage] = useState(initialState.page);

  const [count, setCount] = useState(0);
  const [opportunities, setOpportunities] = useState([]);
  const [cityOptions, setCityOptions] = useState([]);
  const [sourceOptions, setSourceOptions] = useState([]);
  const [facets, setFacets] = useState({});
  const [next, setNext] = useState(null);
  const [previous, setPrevious] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const [showFetchingSpinner, setShowFetchingSpinner] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState('');
  const [reloadToken, setReloadToken] = useState(0);
  const hasInitializedSearchRef = useRef(false);
  const spinnerShownAtRef = useRef(0);
  const spinnerShowTimeoutRef = useRef(null);
  const spinnerHideTimeoutRef = useRef(null);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());

      if (hasInitializedSearchRef.current) {
        setPage(1);
      } else {
        hasInitializedSearchRef.current = true;
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timeoutId);
  }, [searchInput]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const payload = {
      searchInput,
      typeFilter,
      statusFilter,
      cityFilter,
      sourceFilter,
      workModeFilter,
      experienceFilter,
      page,
    };
    try {
      window.sessionStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(payload));
    } catch {
      // Ignore storage errors (e.g., private mode restrictions).
    }
  }, [searchInput, typeFilter, statusFilter, cityFilter, sourceFilter, workModeFilter, experienceFilter, page]);

  useEffect(() => {
    let isCancelled = false;

    const fetchSources = async () => {
      try {
        const sources = await listOpportunitySources();
        if (!isCancelled) {
          setSourceOptions(sources);
          if (sourceFilter && !sources.some((source) => String(source.id) === sourceFilter)) {
            setSourceFilter('');
            setPage(1);
          }
        }
      } catch {
        if (!isCancelled) {
          setSourceOptions([]);
        }
      }
    };

    fetchSources();
    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (spinnerShowTimeoutRef.current) {
        clearTimeout(spinnerShowTimeoutRef.current);
        spinnerShowTimeoutRef.current = null;
      }
      if (spinnerHideTimeoutRef.current) {
        clearTimeout(spinnerHideTimeoutRef.current);
        spinnerHideTimeoutRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (isFetching) {
      if (spinnerHideTimeoutRef.current) {
        clearTimeout(spinnerHideTimeoutRef.current);
        spinnerHideTimeoutRef.current = null;
      }

      if (!showFetchingSpinner && !spinnerShowTimeoutRef.current) {
        spinnerShowTimeoutRef.current = setTimeout(() => {
          spinnerShowTimeoutRef.current = null;
          spinnerShownAtRef.current = Date.now();
          setShowFetchingSpinner(true);
        }, FETCHING_SKELETON_DELAY_MS);
      }
      return undefined;
    }

    if (spinnerShowTimeoutRef.current) {
      clearTimeout(spinnerShowTimeoutRef.current);
      spinnerShowTimeoutRef.current = null;
    }

    if (!showFetchingSpinner) {
      spinnerShownAtRef.current = 0;
      return undefined;
    }

    const elapsedVisibleMs = Date.now() - (spinnerShownAtRef.current || 0);
    const remainingVisibleMs = FETCHING_SKELETON_MIN_VISIBLE_MS - elapsedVisibleMs;

    if (remainingVisibleMs <= 0) {
      spinnerShownAtRef.current = 0;
      setShowFetchingSpinner(false);
      return undefined;
    }

    spinnerHideTimeoutRef.current = setTimeout(() => {
      spinnerHideTimeoutRef.current = null;
      spinnerShownAtRef.current = 0;
      setShowFetchingSpinner(false);
    }, remainingVisibleMs);

    return () => {
      if (spinnerHideTimeoutRef.current) {
        clearTimeout(spinnerHideTimeoutRef.current);
        spinnerHideTimeoutRef.current = null;
      }
    };
  }, [isFetching, showFetchingSpinner]);

  useEffect(() => {
    let isCancelled = false;

    const fetchData = async () => {
      try {
        if (!hasLoadedOnce) {
          setLoading(true);
        } else {
          setIsFetching(true);
        }
        setError('');

        const data = await listOpportunities({
          search: debouncedSearch,
          type: typeFilter,
          status: statusFilter,
          city: cityFilter,
          source: sourceFilter,
          workMode: workModeFilter,
          experienceLevel: experienceFilter,
          sort: DEFAULT_SORT,
          page,
          pageSize: DEFAULT_PAGE_SIZE,
        });

        if (isCancelled) return;

        setCount(data.count ?? 0);
        setNext(data.next ?? null);
        setPrevious(data.previous ?? null);
        setFacets(data.facets ?? {});
        setOpportunities(data.results ?? []);
        setHasLoadedOnce(true);

        const extractedCities = (data.results ?? [])
          .map((item) => String(item?.ville || '').trim())
          .filter(Boolean);
        if (extractedCities.length > 0) {
          setCityOptions((previousCities) => {
            const merged = new Set(previousCities);
            extractedCities.forEach((city) => merged.add(city));
            return Array.from(merged).sort((a, b) => a.localeCompare(b));
          });
        }
      } catch (err) {
        if (isCancelled) return;
        const message =
          err?.response?.data?.detail ||
          'Unable to load opportunities. Please try again.';
        setError(message);

        // Preserve existing data on incremental fetches to avoid list flashing.
        if (!hasLoadedOnce) {
          setOpportunities([]);
          setFacets({});
          setCount(0);
          setNext(null);
          setPrevious(null);
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
          setIsFetching(false);
        }
      }
    };

    fetchData();
    return () => {
      isCancelled = true;
    };
  }, [
    debouncedSearch,
    typeFilter,
    statusFilter,
    cityFilter,
    sourceFilter,
    workModeFilter,
    experienceFilter,
    page,
    reloadToken,
  ]);

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

  const setCityFilterAndResetPage = (value) => {
    setCityFilter(value);
    setPage(1);
  };

  const setSourceFilterAndResetPage = (value) => {
    setSourceFilter(value);
    setPage(1);
  };

  const setWorkModeFilterAndResetPage = (value) => {
    setWorkModeFilter(value);
    setPage(1);
  };

  const setExperienceFilterAndResetPage = (value) => {
    setExperienceFilter(value);
    setPage(1);
  };

  const resetFilters = () => {
    setSearchInput('');
    setDebouncedSearch('');
    setTypeFilter('');
    setStatusFilter('');
    setCityFilter('');
    setSourceFilter('');
    setWorkModeFilter('');
    setExperienceFilter('');
    setPage(1);
  };

  const refetch = () => setReloadToken((prev) => prev + 1);

  return {
    opportunities,
    cityOptions,
    sourceOptions,
    facets,
    count,
    next,
    previous,
    page,
    totalPages,
    hasNext: Boolean(next),
    hasPrevious: Boolean(previous),
    loading,
    isFetching,
    showFetchingSpinner,
    error,
    searchInput,
    setSearchInput,
    typeFilter,
    setTypeFilter: setTypeFilterAndResetPage,
    statusFilter,
    setStatusFilter: setStatusFilterAndResetPage,
    cityFilter,
    setCityFilter: setCityFilterAndResetPage,
    sourceFilter,
    setSourceFilter: setSourceFilterAndResetPage,
    workModeFilter,
    setWorkModeFilter: setWorkModeFilterAndResetPage,
    experienceFilter,
    setExperienceFilter: setExperienceFilterAndResetPage,
    setPage,
    resetFilters,
    refetch,
  };
};

export default useOpportunitiesBrowse;
