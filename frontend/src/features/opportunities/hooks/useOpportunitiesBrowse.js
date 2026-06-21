import { useEffect, useMemo, useRef, useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import {
  DEFAULT_BROWSE_STATE,
  DEFAULT_SORT,
  DEFAULT_PAGE_SIZE,
  FETCHING_SKELETON_DELAY_MS,
  FETCHING_SKELETON_MIN_VISIBLE_MS,
  FILTERS_STORAGE_KEY,
  SEARCH_DEBOUNCE_MS,
} from '../constants/opportunityBrowse.js';
import {
  listOpportunities,
  listOpportunitySources,
} from '../services/opportunitiesService.js';

const URL_TYPE_FILTERS = new Set(['EMPLOI', 'STAGE', 'SAISONNIER', 'RECHERCHE', 'PROJET', 'FINANCEMENT']);
const OPPORTUNITIES_STALE_TIME_MS = 5 * 60 * 1000;

const readUrlTypeFilter = () => {
  if (typeof window === 'undefined') return '';
  const rawType = new URLSearchParams(window.location.search).get('type');
  const normalized = String(rawType || '').trim().toUpperCase();
  return URL_TYPE_FILTERS.has(normalized) ? normalized : '';
};

const getBrowseSort = ({ hasSearch, typeFilter }) => {
  if (hasSearch) return 'relevance';
  return typeFilter === 'PROJET' ? 'deadline' : DEFAULT_SORT;
};

const getDatePostedParam = ({ typeFilter, datePostedFilter }) =>
  typeFilter === 'PROJET' ? '' : datePostedFilter;

const getDeadlineWindowParam = ({ typeFilter, datePostedFilter }) =>
  typeFilter === 'PROJET' ? datePostedFilter : '';

const buildScopedStorageKey = (baseKey, storageScopeKey) =>
  storageScopeKey ? `${baseKey}:${storageScopeKey}` : baseKey;

const readPersistedBrowseState = (storageScopeKey = '') => {
  if (typeof window === 'undefined') return DEFAULT_BROWSE_STATE;
  const urlTypeFilter = readUrlTypeFilter();
  if (urlTypeFilter) {
    return {
      ...DEFAULT_BROWSE_STATE,
      typeFilter: urlTypeFilter,
    };
  }

  try {
    const raw = window.sessionStorage.getItem(buildScopedStorageKey(FILTERS_STORAGE_KEY, storageScopeKey));
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
      datePostedFilter: String(parsed?.datePostedFilter || ''),
      page: Number.isFinite(page) && page > 0 ? page : 1,
    };
  } catch {
    return DEFAULT_BROWSE_STATE;
  }
};

const getQueryErrorMessage = (error) => {
  if (!error) return '';
  return error?.response?.data?.detail || 'Unable to load opportunities. Please try again.';
};

export const useOpportunitiesBrowse = ({
  enabled = true,
  lockedTypeFilter = '',
  storageScopeKey = '',
} = {}) => {
  const [initialState] = useState(() => readPersistedBrowseState(storageScopeKey));
  const [activeStorageScopeKey, setActiveStorageScopeKey] = useState(storageScopeKey);
  const [searchInput, setSearchInput] = useState(initialState.searchInput);
  const [debouncedSearch, setDebouncedSearch] = useState(initialState.searchInput.trim());
  const [typeFilter, setTypeFilter] = useState(initialState.typeFilter);
  const [statusFilter, setStatusFilter] = useState(initialState.statusFilter);
  const [cityFilter, setCityFilter] = useState(initialState.cityFilter);
  const [sourceFilter, setSourceFilter] = useState(initialState.sourceFilter);
  const [workModeFilter, setWorkModeFilter] = useState(initialState.workModeFilter);
  const [experienceFilter, setExperienceFilter] = useState(initialState.experienceFilter);
  const [datePostedFilter, setDatePostedFilter] = useState(initialState.datePostedFilter);
  const [page, setPage] = useState(initialState.page);
  const [cityOptions, setCityOptions] = useState([]);
  const [showFetchingSpinner, setShowFetchingSpinner] = useState(false);
  const effectiveTypeFilter = lockedTypeFilter || typeFilter;
  const hasInitializedSearchRef = useRef(false);
  const previousStorageScopeKeyRef = useRef(storageScopeKey);
  const spinnerShownAtRef = useRef(0);
  const spinnerShowTimeoutRef = useRef(null);
  const spinnerHideTimeoutRef = useRef(null);
  const storageScopeReady = activeStorageScopeKey === storageScopeKey;
  const queryEnabled = Boolean(enabled && storageScopeReady);
  const hasSearch = debouncedSearch.length > 0;
  const datePostedParam = getDatePostedParam({
    typeFilter: effectiveTypeFilter,
    datePostedFilter,
  });
  const deadlineWindowParam = getDeadlineWindowParam({
    typeFilter: effectiveTypeFilter,
    datePostedFilter,
  });
  const browseSort = getBrowseSort({ hasSearch, typeFilter: effectiveTypeFilter });
  const opportunityQueryParams = useMemo(
    () => ({
      scope: activeStorageScopeKey,
      search: debouncedSearch,
      type: effectiveTypeFilter,
      status: statusFilter,
      city: cityFilter,
      source: sourceFilter,
      workMode: workModeFilter,
      experience: experienceFilter,
      datePosted: datePostedParam,
      deadlineWindow: deadlineWindowParam,
      sort: browseSort,
      page,
      pageSize: DEFAULT_PAGE_SIZE,
    }),
    [
      activeStorageScopeKey,
      browseSort,
      cityFilter,
      datePostedParam,
      deadlineWindowParam,
      debouncedSearch,
      effectiveTypeFilter,
      experienceFilter,
      page,
      sourceFilter,
      statusFilter,
      workModeFilter,
    ],
  );
  const opportunitiesQuery = useQuery({
    queryKey: ['opportunities', 'list', opportunityQueryParams],
    queryFn: () =>
      listOpportunities({
        search: opportunityQueryParams.search,
        type: opportunityQueryParams.type,
        status: opportunityQueryParams.status,
        city: opportunityQueryParams.city,
        source: opportunityQueryParams.source,
        workMode: opportunityQueryParams.workMode,
        experienceLevel: opportunityQueryParams.experience,
        datePosted: opportunityQueryParams.datePosted,
        deadlineWindow: opportunityQueryParams.deadlineWindow,
        sort: opportunityQueryParams.sort,
        page: opportunityQueryParams.page,
        pageSize: opportunityQueryParams.pageSize,
      }),
    enabled: queryEnabled,
    staleTime: OPPORTUNITIES_STALE_TIME_MS,
    placeholderData: keepPreviousData,
  });
  const sourcesQuery = useQuery({
    queryKey: ['opportunities', 'sources'],
    queryFn: listOpportunitySources,
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    enabled: queryEnabled,
  });
  const sourceOptions = sourcesQuery.data ?? [];
  const data = opportunitiesQuery.data;
  const opportunities = data?.results ?? [];
  const count = data?.count ?? 0;
  const facets = data?.facets ?? {};
  const next = data?.next ?? null;
  const previous = data?.previous ?? null;
  const activeQuery = opportunitiesQuery;
  const loading = Boolean(queryEnabled && activeQuery.isLoading);
  const isFetching = Boolean(queryEnabled && activeQuery.isFetching);
  const error = getQueryErrorMessage(activeQuery.error);

  useEffect(() => {
    if (!sourceFilter) return;
    if (sourceOptions.length === 0) return;
    if (!sourceOptions.some((source) => String(source.id) === sourceFilter)) {
      setSourceFilter('');
      setPage(1);
    }
  }, [sourceOptions, sourceFilter]);

  useEffect(() => {
    if (!enabled) return undefined;

    const timeoutId = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());

      if (hasInitializedSearchRef.current) {
        setPage(1);
      } else {
        hasInitializedSearchRef.current = true;
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timeoutId);
  }, [enabled, searchInput]);

  useEffect(() => {
    if (previousStorageScopeKeyRef.current === storageScopeKey) return;
    previousStorageScopeKeyRef.current = storageScopeKey;

    const nextState = readPersistedBrowseState(storageScopeKey);
    hasInitializedSearchRef.current = false;
    setSearchInput(nextState.searchInput);
    setDebouncedSearch(nextState.searchInput.trim());
    setTypeFilter(nextState.typeFilter);
    setStatusFilter(nextState.statusFilter);
    setCityFilter(nextState.cityFilter);
    setSourceFilter(nextState.sourceFilter);
    setWorkModeFilter(nextState.workModeFilter);
    setExperienceFilter(nextState.experienceFilter);
    setDatePostedFilter(nextState.datePostedFilter);
    setPage(nextState.page);
    setActiveStorageScopeKey(storageScopeKey);
  }, [storageScopeKey]);

  useEffect(() => {
    if (!enabled || !storageScopeReady) return;
    if (typeof window === 'undefined') return;

    const payload = {
      searchInput,
      typeFilter: effectiveTypeFilter,
      statusFilter,
      cityFilter,
      sourceFilter,
      workModeFilter,
      experienceFilter,
      datePostedFilter,
      page,
    };
    try {
      window.sessionStorage.setItem(
        buildScopedStorageKey(FILTERS_STORAGE_KEY, storageScopeKey),
        JSON.stringify(payload),
      );
    } catch {
      // Ignore storage errors (e.g., private mode restrictions).
    }
  }, [
    cityFilter,
    datePostedFilter,
    effectiveTypeFilter,
    enabled,
    experienceFilter,
    page,
    searchInput,
    sourceFilter,
    statusFilter,
    storageScopeKey,
    storageScopeReady,
    workModeFilter,
  ]);

  useEffect(() => {
    if (!data) return;

    const facetCities = (data.facets?.locations ?? [])
      .map((item) => String(item?.key || '').trim())
      .filter(Boolean);
    if (facetCities.length > 0) {
      setCityOptions(facetCities);
      return;
    }

    const extractedCities = (data.results ?? [])
      .map((item) => String(item?.ville || '').trim())
      .filter(Boolean);
    if (extractedCities.length > 0) {
      setCityOptions(Array.from(new Set(extractedCities)).sort((a, b) => a.localeCompare(b)));
    }
  }, [data]);

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

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(count / DEFAULT_PAGE_SIZE)),
    [count],
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

  const setDatePostedFilterAndResetPage = (value) => {
    setDatePostedFilter(value);
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
    setDatePostedFilter('');
    setPage(1);
  };

  const refetch = () => activeQuery.refetch();

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
    typeFilter: effectiveTypeFilter,
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
    datePostedFilter,
    setDatePostedFilter: setDatePostedFilterAndResetPage,
    setPage,
    resetFilters,
    refetch,
  };
};

export default useOpportunitiesBrowse;
