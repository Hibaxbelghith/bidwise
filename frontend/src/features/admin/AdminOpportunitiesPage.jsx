import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, ExternalLink, Eye, Search, Trash2, X } from 'lucide-react';

import { Badge } from '../../components/ui/badge.jsx';
import { Button } from '../../components/ui/button.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card.jsx';
import { Input } from '../../components/ui/input.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from '../../components/ui/select.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table.jsx';
import adminApi from '../../lib/adminApi.js';


const PAGE_SIZE = 20;
const VISIBLE_PAGE_BUTTONS = 5;
const SEARCH_DEBOUNCE_MS = 350;
const INITIAL_LOADING_MIN_MS = 900;
const REFRESH_LOADING_MIN_MS = 500;

const getSourceName = (source) => {
  if (!source) return '';
  if (typeof source === 'string') return source;
  if (typeof source === 'object') return source.nom || '';
  return '';
};

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).format(date);
};

const statusClassName = (status) => {
  const value = String(status || '').toLowerCase();
  if (value === 'active') return 'border-green-200 bg-green-50 text-green-700';
  if (value === 'rejected') return 'border-red-200 bg-red-50 text-red-700';
  if (value === 'archivee' || value === 'archived') return 'border-neutral-200 bg-neutral-100 text-neutral-700';
  if (value === 'expiree' || value === 'expired') return 'border-yellow-200 bg-yellow-50 text-yellow-700';
  return 'border-neutral-200 bg-white text-neutral-700';
};

const sourceClassName = (source) => {
  const value = getSourceName(source).toLowerCase();
  if (value.includes('linkedin')) return 'border-blue-200 bg-blue-50 text-blue-700';
  if (value.includes('keejob')) return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  return 'border-neutral-200 bg-neutral-50 text-neutral-700';
};

const normalizeSources = (data) => {
  if (!Array.isArray(data)) return [];

  const seenIds = new Set();
  return data.filter((item) => {
    const id = item?.id;
    const name = item?.nom;
    if (id == null || !name || seenIds.has(id)) return false;
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

const useDebouncedValue = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [delay, value]);

  return debouncedValue;
};

const getVisiblePageNumbers = (currentPage, totalPages) => {
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

const SkeletonRow = () => (
  <TableRow>
    <TableCell className="px-4 py-4">
      <div className="space-y-2">
        <div className="h-4 w-48 rounded bg-neutral-200 animate-pulse" />
        <div className="h-3 w-28 rounded bg-neutral-100 animate-pulse" />
      </div>
    </TableCell>
    <TableCell className="px-4 py-4">
      <div className="h-6 w-20 rounded-full bg-neutral-100 animate-pulse" />
    </TableCell>
    <TableCell className="px-4 py-4">
      <div className="h-4 w-20 rounded bg-neutral-100 animate-pulse" />
    </TableCell>
    <TableCell className="px-4 py-4">
      <div className="h-6 w-20 rounded-full bg-neutral-100 animate-pulse" />
    </TableCell>
    <TableCell className="px-4 py-4">
      <div className="flex justify-end gap-2">
        <div className="h-9 w-20 rounded-md bg-neutral-100 animate-pulse" />
        <div className="h-9 w-20 rounded-md bg-neutral-100 animate-pulse" />
      </div>
    </TableCell>
  </TableRow>
);

const AdminOpportunitiesPage = () => {
  const [opportunities, setOpportunities] = useState([]);
  const [sources, setSources] = useState([]);
  const [searchDraft, setSearchDraft] = useState('');
  const [source, setSource] = useState('');
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSourcesLoading, setIsSourcesLoading] = useState(true);
  const [error, setError] = useState('');
  const [sourcesError, setSourcesError] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const latestOpportunitiesRequest = useRef(0);
  const sectionRef = useRef(null);
  const didMountRef = useRef(false);
  const debouncedSearch = useDebouncedValue(searchDraft.trim(), SEARCH_DEBOUNCE_MS);

  const totalPages = Math.max(Math.ceil(count / PAGE_SIZE), 1);
  const isInitialLoading = isLoading && !hasLoadedOnce;
  const isRefreshing = isLoading && hasLoadedOnce;
  const currentPageSize = opportunities.length;

  const pageRangeLabel = useMemo(() => {
    if (!count || !currentPageSize) return '0-0';
    const start = (page - 1) * PAGE_SIZE + 1;
    const end = start + currentPageSize - 1;
    return `${start}-${end}`;
  }, [count, currentPageSize, page]);
  const visiblePageNumbers = useMemo(
    () => getVisiblePageNumbers(page, totalPages),
    [page, totalPages]
  );

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, source]);

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

        const params = { page };
        if (debouncedSearch) params.search = debouncedSearch;
        if (source) params.source = Number(source);

        const { data } = await adminApi.get('/admin/opportunities/', {
          params,
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
  }, [debouncedSearch, page, reloadKey, source]);

  useEffect(() => {
    const controller = new AbortController();
    const requestStartedAt = Date.now();

    const loadSources = async () => {
      try {
        setIsSourcesLoading(true);
        setSourcesError('');
        const { data } = await adminApi.get('/sources/', {
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

  useEffect(() => {
    if (!didMountRef.current) {
      didMountRef.current = true;
      return;
    }

    sectionRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  }, [page]);

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    setPage(1);
  };

  const handleSourceChange = (value) => {
    setPage(1);
    setSource(value);
  };

  const handleDelete = async (opportunity) => {
    const confirmed = window.confirm(`Delete "${opportunity.title}"?`);
    if (!confirmed) return;

    try {
      setDeletingId(opportunity.id);
      await adminApi.delete(`/admin/opportunities/${opportunity.id}/`);
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

  return (
    <section ref={sectionRef} className="bg-neutral-50" aria-labelledby="admin-opportunities-heading">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 id="admin-opportunities-heading" className="text-3xl font-bold text-neutral-900">
              Opportunities
            </h1>
            <p className="mt-2 text-sm text-neutral-600">Review, filter, and remove imported opportunities.</p>
          </div>

          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleSearchSubmit}>
            <div className="relative sm:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" aria-hidden="true" />
              <Input
                type="search"
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                className="pl-9"
                placeholder="Search title"
                aria-label="Search by title"
              />
            </div>
            <Select value={source} onValueChange={handleSourceChange}>
              <SelectTrigger className="sm:w-48" disabled={isSourcesLoading}>
                <span />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All sources</SelectItem>
                {sources.map((option) => (
                  <SelectItem key={option.id} value={String(option.id)}>
                    {option.nom}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="submit" disabled={isLoading}>
              <Search className="h-4 w-4" aria-hidden="true" />
              Search
            </Button>
          </form>
        </div>

        {error || sourcesError ? (
          <div className="mb-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
            {error || sourcesError}
          </div>
        ) : null}

        <Card className="overflow-hidden">
          <CardHeader className="flex flex-col gap-2 border-b border-neutral-200 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-base">Opportunity list</CardTitle>
            <div className="flex items-center gap-3 text-sm text-neutral-500">
              {isSourcesLoading ? <div className={`h-4 w-16 rounded bg-neutral-200 animate-pulse`} /> : null}
              <span>{count} total</span>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-neutral-50">
                  <TableHead className="px-4 py-3">Title</TableHead>
                  <TableHead className="px-4 py-3">Source</TableHead>
                  <TableHead className="px-4 py-3">Date</TableHead>
                  <TableHead className="px-4 py-3">Status</TableHead>
                  <TableHead className="px-4 py-3 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody
                aria-busy={isLoading}
                style={{
                  opacity: isRefreshing ? 0.4 : 1,
                  pointerEvents: isRefreshing ? 'none' : 'auto',
                  transition: 'opacity 150ms ease',
                }}
              >
                {isInitialLoading ? (
                  Array.from({ length: 6 }).map((_, index) => <SkeletonRow key={index} />)
                ) : opportunities.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="px-4 py-10 text-center text-neutral-500">
                      No opportunities found.
                    </TableCell>
                  </TableRow>
                ) : opportunities.map((opportunity) => (
                  <TableRow key={opportunity.id}>
                    <TableCell className="max-w-[420px] px-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-neutral-900">{opportunity.title}</p>
                        {opportunity.company_name ? (
                          <p className="truncate text-xs text-neutral-500">{opportunity.company_name}</p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <Badge variant="outline" className={sourceClassName(opportunity.source)}>
                        {getSourceName(opportunity.source) || 'unknown'}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-neutral-600">{formatDate(opportunity.created_at)}</TableCell>
                    <TableCell className="px-4 py-3">
                      <Badge variant="outline" className={statusClassName(opportunity.status)}>
                        {opportunity.status || 'unknown'}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={isLoading}
                          onClick={() => setSelectedOpportunity(opportunity)}
                        >
                          <Eye className="h-4 w-4" aria-hidden="true" />
                          View
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          disabled={deletingId === opportunity.id || isLoading}
                          onClick={() => handleDelete(opportunity)}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                          {deletingId === opportunity.id ? 'Deleting' : 'Delete'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-neutral-500">
            Showing {pageRangeLabel} of {count} opportunities
          </p>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!hasPrevious || isLoading}
              onClick={() => setPage((currentPage) => Math.max(currentPage - 1, 1))}
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
                  onClick={() => setPage(1)}
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
                onClick={() => setPage(pageNumber)}
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
                  onClick={() => setPage(totalPages)}
                >
                  {totalPages}
                </Button>
              </>
            ) : null}
            <Button
              type="button"
              variant="outline"
              disabled={!hasNext || isLoading}
              onClick={() => setPage((currentPage) => currentPage + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>

      {selectedOpportunity ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/60 px-4 py-6">
          <div className="w-full max-w-lg rounded-lg bg-white shadow-xl" role="dialog" aria-modal="true">
            <div className="flex items-start justify-between gap-4 border-b border-neutral-200 p-5">
              <div>
                <h2 className="text-lg font-semibold text-neutral-900">{selectedOpportunity.title}</h2>
                <p className="mt-1 text-sm text-neutral-500">{selectedOpportunity.company_name || 'Unknown company'}</p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setSelectedOpportunity(null)}
                aria-label="Close"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            <div className="space-y-4 p-5 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className={sourceClassName(selectedOpportunity.source)}>
                  {getSourceName(selectedOpportunity.source) || 'unknown'}
                </Badge>
                <Badge variant="outline" className={statusClassName(selectedOpportunity.status)}>
                  {selectedOpportunity.status || 'unknown'}
                </Badge>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-medium uppercase text-neutral-500">Created</p>
                  <p className="mt-1 text-neutral-900">{formatDate(selectedOpportunity.created_at)}</p>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase text-neutral-500">ID</p>
                  <p className="mt-1 text-neutral-900">{selectedOpportunity.id}</p>
                </div>
              </div>
              {selectedOpportunity.url ? (
                <a
                  href={selectedOpportunity.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 text-sm font-medium text-blue-700 hover:text-blue-900"
                >
                  <ExternalLink className="h-4 w-4" aria-hidden="true" />
                  Open source URL
                </a>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
};

export default AdminOpportunitiesPage;
