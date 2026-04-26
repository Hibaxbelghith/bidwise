import { useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Building2,
  CalendarDays,
  Lock,
  MapPin,
  Search,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';

import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { useAuth } from '../auth/AuthContext.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { useOpportunities } from './useOpportunities';
import { cleanDescription } from './utils/text.js';

const TYPE_OPTIONS = [
  { value: 'EMPLOI', label: 'Job' },
  { value: 'STAGE', label: 'Internship' },
  { value: 'SAISONNIER', label: 'Seasonal' },
  { value: 'RECHERCHE', label: 'Research' },
  { value: 'PROJET', label: 'Project' },
  { value: 'FINANCEMENT', label: 'Funding' },
];

const STATUS_OPTIONS = [
  { value: 'ACTIVE', label: 'Active' },
  { value: 'EXPIREE', label: 'Expired' },
  { value: 'ARCHIVEE', label: 'Archived' },
];

const ORDER_OPTIONS = [
  { value: '-date_publication', label: 'Most recent' },
  { value: 'date_publication', label: 'Oldest first' },
  { value: 'date_limite', label: 'Deadline' },
];

const TYPE_LABELS = TYPE_OPTIONS.reduce((acc, item) => {
  acc[item.value] = item.label;
  return acc;
}, {});

const STATUS_LABELS = STATUS_OPTIONS.reduce((acc, item) => {
  acc[item.value] = item.label;
  return acc;
}, {});

const ANONYMOUS_ORGANIZATION_PATTERN = /entreprise\s+anonyme/i;
const API_BASE_URL = String(import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

const formatDate = (value) => {
  if (!value) return 'N/A';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
};

const toSafeNonNegativeInt = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.floor(parsed);
};

const formatOrganizationLabel = (opportunity) => {
  const organization = String(opportunity?.organisation_nom || '').trim();
  if (!organization || ANONYMOUS_ORGANIZATION_PATTERN.test(organization)) return '';
  return organization;
};

const buildCompanyInitialsAvatar = (label) => {
  const words = String(label || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  const initials = words.map((word) => word[0]?.toUpperCase() || '').join('') || 'BW';
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
      <rect width="96" height="96" rx="20" fill="#f1f5f9" />
      <text x="50%" y="52%" dominant-baseline="middle" text-anchor="middle"
            font-family="Arial, sans-serif" font-size="32" font-weight="700" fill="#0f172a">${initials}</text>
    </svg>
  `;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
};

const formatExperienceLabel = (opportunity) => {
  const experience = opportunity?.experience;
  if (!experience || typeof experience !== 'object') return '';

  const min = toSafeNonNegativeInt(experience.min);
  const max = toSafeNonNegativeInt(experience.max);

  if (min === null && max === null) return '';
  if (min === 0 && (max === null || max <= 1)) return 'Entry level';
  if (min !== null && max !== null) {
    return min === max ? `${min} years` : `${min}-${max} years`;
  }
  if (min !== null) return `${min}+ years`;
  return `Up to ${max} years`;
};

const dedupeStrings = (items) => {
  const result = [];
  const seen = new Set();

  for (const value of items || []) {
    const normalized = String(value || '').trim();
    if (!normalized) continue;

    const key = normalized.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(normalized);
  }

  return result;
};

const getLanguagePreview = (opportunity) => {
  const values = dedupeStrings(opportunity?.languages || opportunity?.languages_fallback || []);
  return values.slice(0, 2);
};

const sanitizeCompanyLogoUrl = (rawLogo) => {
  const value = String(rawLogo || '').trim();
  if (!value) return '';

  try {
    const url = new URL(value);
    if (url.hostname.includes('media.licdn.com')) {
      url.searchParams.delete('t');
      return url.toString();
    }
  } catch {
    return value;
  }

  return value;
};

const getBackendOrigin = () => {
  try {
    return new URL(API_BASE_URL, window.location.origin).origin;
  } catch {
    return window.location.origin;
  }
};

const getCompanyLogoAsset = (opportunity) => {
  const rawLogo =
    opportunity?.logo_url || opportunity?.organisation_logo || opportunity?.company_logo || '';
  const sanitizedUrl = sanitizeCompanyLogoUrl(rawLogo);
  if (!sanitizedUrl) {
    return { src: '', fallbackSrc: '' };
  }

  if (sanitizedUrl.startsWith('/media/')) {
    const backendOrigin = getBackendOrigin();
    return {
      src: `${backendOrigin}${sanitizedUrl}`,
      fallbackSrc: '',
    };
  }

  try {
    const url = new URL(sanitizedUrl);
    if (url.hostname.includes('media.licdn.com')) {
      return {
        src: sanitizedUrl,
        fallbackSrc: '',
      };
    }
  } catch {
    return { src: sanitizedUrl, fallbackSrc: '' };
  }

  return { src: sanitizedUrl, fallbackSrc: '' };
};

const truncate = (text, max = 220) => {
  const normalizedText = String(text || '').trim();
  if (!normalizedText) return '';
  return normalizedText.length > max ? `${normalizedText.slice(0, max)}...` : normalizedText;
};

const stripHtmlTags = (value) =>
  String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();

const decodeHtmlEntities = (value) => {
  const rawValue = String(value || '');
  if (!rawValue.includes('&')) return rawValue;
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return rawValue;
  }

  const parser = new DOMParser();
  const doc = parser.parseFromString(`<!doctype html><body>${rawValue}`, 'text/html');
  return String(doc.body?.textContent || '').trim();
};

const buildDescriptionPreview = (opportunity) => {
  const htmlDescription = String(opportunity?.description_html || '').trim();
  const sourceText = htmlDescription
    ? decodeHtmlEntities(stripHtmlTags(htmlDescription))
    : cleanDescription(opportunity?.description);

  return truncate(sourceText, 240);
};

const getCardAiHint = (opportunity, isUserAuthenticated) => {
  if (!isUserAuthenticated) {
    return 'AI Match locked';
  }

  const raw = Number(opportunity?.similarity_score);
  if (!Number.isFinite(raw)) {
    return 'AI Match in detail';
  }

  const clamped = Math.max(0, Math.min(raw, 1));
  const percentage = Math.round(clamped * 100);
  return `AI Match ${percentage}%`;
};

const SkeletonOpportunityCard = ({ compact = false }) => (
  <article className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <div className="animate-pulse space-y-4">
      <div className="flex items-start gap-4">
        <div className="h-12 w-12 shrink-0 rounded-xl bg-neutral-200" />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="h-4 w-3/4 rounded bg-neutral-200" />
          <div className="h-3 w-1/2 rounded bg-neutral-100" />
        </div>
      </div>

      {!compact && (
        <>
          <div className="flex flex-wrap gap-2">
            <div className="h-3 w-24 rounded-full bg-neutral-100" />
            <div className="h-3 w-28 rounded-full bg-neutral-100" />
            <div className="h-3 w-20 rounded-full bg-neutral-100" />
          </div>
          <div className="space-y-2">
            <div className="h-3 w-full rounded bg-neutral-100" />
            <div className="h-3 w-11/12 rounded bg-neutral-100" />
            <div className="h-3 w-2/3 rounded bg-neutral-100" />
          </div>
        </>
      )}
    </div>
  </article>
);

const FetchingSkeletonBanner = () => (
  <div className="mb-4 rounded-xl border border-neutral-200 bg-white px-4 py-3 shadow-sm">
    <div className="animate-pulse space-y-2">
      <div className="h-2 w-36 rounded-full bg-neutral-200" />
      <div className="h-2 w-full rounded-full bg-neutral-100" />
    </div>
  </div>
);

const GuestLockPanel = () => (
  <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4 shadow-sm">
    <p className="mb-3 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-700">
      <Lock className="h-4 w-4" />
      Guest mode
    </p>
    <h2 className="text-base font-semibold text-blue-900">Core data is open, AI intelligence is locked</h2>
    <p className="mt-2 text-sm leading-6 text-blue-900/90">
      Browse title, company, location, salary, skills and descriptions. Login to unlock match
      score, recommendations, and action shortcuts.
    </p>
    <Button asChild className="mt-4 w-full sm:w-auto">
      <Link to="/login">Login to unlock</Link>
    </Button>
  </div>
);

const AuthValuePanel = () => (
  <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
    <p className="mb-3 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-emerald-700">
      <Sparkles className="h-4 w-4" />
      Signed in
    </p>
    <h2 className="text-base font-semibold text-emerald-900">AI insights are available on each opportunity</h2>
    <p className="mt-2 text-sm leading-6 text-emerald-900/90">
      Open any detail page to access match score, explainability insights, and action workflow.
    </p>
  </div>
);

export function OpportunitiesBrowse() {
  const resultsSectionRef = useRef(null);
  const { isAuthenticated, loading: authLoading } = useAuth();
  const {
    opportunities,
    cityOptions,
    count,
    page,
    totalPages,
    hasNext,
    hasPrevious,
    loading,
    isFetching,
    showFetchingSpinner,
    error,
    searchInput,
    setSearchInput,
    typeFilter,
    setTypeFilter,
    statusFilter,
    setStatusFilter,
    cityFilter,
    setCityFilter,
    ordering,
    setOrdering,
    setPage,
    resetFilters,
    refetch,
  } = useOpportunities();

  const isUserAuthenticated = !authLoading && isAuthenticated;

  const hasActiveFilters =
    Boolean(searchInput || typeFilter || statusFilter || cityFilter) ||
    ordering !== '-date_publication';

  const countLabel = useMemo(() => {
    if (loading && opportunities.length === 0) return 'Loading opportunities...';
    if (count <= 0) return 'No opportunities found for current filters';
    return `${count} opportunities found`;
  }, [count, loading, opportunities.length]);   

  const scrollToResultsTop = () => {
    if (typeof window === 'undefined') return;

    if (resultsSectionRef.current) {
      resultsSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePreviousPage = () => {
    setPage((prev) => Math.max(1, prev - 1));
    scrollToResultsTop();
  };

  const handleNextPage = () => {
    setPage((prev) => prev + 1);
    scrollToResultsTop();
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_390px]">
            <div>
              <p className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <Sparkles className="h-4 w-4" />
                BidWise Opportunity Explorer
              </p>
              <h1 className="text-3xl font-bold tracking-tight text-neutral-900">Browse Opportunities</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
                Discover jobs, internships, projects, and funding opportunities with a clean,
                focused workflow.
              </p>
            </div>
            {isUserAuthenticated ? <AuthValuePanel /> : <GuestLockPanel />}
          </div>
        </div>
      </header>

      <section className="sticky top-0 z-20 border-b border-neutral-200 bg-white/95 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="mb-3 flex items-center justify-between gap-2">
            {hasActiveFilters ? (
              <Button size="sm" variant="ghost" onClick={resetFilters}>
                Reset filters
              </Button>
            ) : null}
          </div>

          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-6">
            <div className="relative lg:col-span-2">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
              <Input
                type="text"
                placeholder="Search title or description"
                className="pl-9"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </div>

            <Input
              type="text"
              placeholder="Filter by city"
              value={cityFilter}
              list="city-filter-options"
              onChange={(event) => setCityFilter(event.target.value)}
            />
            <datalist id="city-filter-options">
              {cityOptions.map((city) => (
                <option key={city} value={city} />
              ))}
            </datalist>

            <Select
              value={typeFilter || 'all'}
              onValueChange={(value) => setTypeFilter(value === 'all' ? '' : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                {TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={statusFilter || 'all'}
              onValueChange={(value) => setStatusFilter(value === 'all' ? '' : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={ordering} onValueChange={setOrdering}>
              <SelectTrigger>
                <SelectValue placeholder="Sort" />
              </SelectTrigger>
              <SelectContent>
                {ORDER_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

        </div>
      </section>

      <section ref={resultsSectionRef} className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium text-neutral-700">{countLabel}</p>
          <p className="text-sm text-neutral-600">
            Page {page} of {totalPages}
          </p>
        </div>

        {showFetchingSpinner && opportunities.length > 0 && <FetchingSkeletonBanner />}

        {loading && opportunities.length === 0 ? (
          <div className="space-y-4">
            {[0, 1, 2].map((index) => (
              <SkeletonOpportunityCard key={index} />
            ))}
          </div>
        ) : null}

        {!loading && error && opportunities.length === 0 ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
            <p className="mb-3">{error}</p>
            <Button variant="outline" onClick={refetch}>
              Retry
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
            <h2 className="mb-2 text-lg font-semibold text-neutral-900">No opportunities found</h2>
            <p className="text-neutral-600">Try adjusting search terms or filters.</p>
            <div className="mt-4">
              <Button variant="outline" onClick={resetFilters}>
                Reset filters
              </Button>
            </div>
          </div>
        ) : null}

        {!loading && opportunities.length > 0 ? (
          <div className="space-y-4">
            {opportunities.map((opportunity) => {
              const salaryLabel = String(opportunity?.salary || '').trim();
              const experienceLabel = formatExperienceLabel(opportunity);
              const languagePreview = getLanguagePreview(opportunity);
              const companyLogo = getCompanyLogoAsset(opportunity);
              const descriptionPreview = buildDescriptionPreview(opportunity);
              const aiHint = getCardAiHint(opportunity, isUserAuthenticated);

              return (
                <article
                  key={opportunity.id}
                  className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="mb-3 flex items-start gap-4">
                    <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-neutral-200 bg-white">
                      <Building2 className="h-5 w-5 text-neutral-400" />
                      {companyLogo.src ? (
                        <img
                          src={companyLogo.src}
                          data-fallback-src={companyLogo.fallbackSrc || ''}
                          alt={`${formatOrganizationLabel(opportunity)} logo`}
                          className="absolute inset-0 h-full w-full rounded-xl bg-white object-contain"
                          loading="lazy"
                          onError={(event) => {
                            const fallbackSrc = event.currentTarget.dataset.fallbackSrc || '';
                            if (fallbackSrc && event.currentTarget.src !== fallbackSrc) {
                              event.currentTarget.src = fallbackSrc;
                              event.currentTarget.dataset.fallbackSrc = '';
                              return;
                            }
                            event.currentTarget.src = buildCompanyInitialsAvatar(
                              formatOrganizationLabel(opportunity)
                            );
                            event.currentTarget.dataset.fallbackSrc = '';
                          }}
                        />
                      ) : null}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <Link
                          to={`/opportunities/${opportunity.id}`}
                          className="text-lg font-semibold leading-tight text-neutral-900 hover:text-blue-700"
                        >
                          {opportunity.titre || 'Untitled opportunity'}
                        </Link>
                        <Badge variant="secondary">
                          {TYPE_LABELS[opportunity.type_opportunite] ||
                            opportunity.type_opportunite ||
                            'N/A'}
                        </Badge>
                        <Badge variant={opportunity.statut === 'ACTIVE' ? 'default' : 'outline'}>
                          {STATUS_LABELS[opportunity.statut] || opportunity.statut || 'N/A'}
                        </Badge>
                        <Badge
                          variant="outline"
                          className={isUserAuthenticated ? 'border-blue-200 bg-blue-50 text-blue-700' : ''}
                        >
                          {isUserAuthenticated ? aiHint : (
                            <span className="inline-flex items-center gap-1">
                              <Lock className="h-3 w-3" />
                              {aiHint}
                            </span>
                          )}
                        </Badge>
                      </div>

                      <div className="mb-3 flex flex-wrap gap-x-4 gap-y-2 text-sm text-neutral-700">
                        {formatOrganizationLabel(opportunity) ? (
                          <span className="inline-flex items-center gap-1">
                            <Building2 className="h-4 w-4" />
                            {formatOrganizationLabel(opportunity)}
                          </span>
                        ) : null}
                        {String(opportunity.ville || '').trim() ? (
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="h-4 w-4" />
                            {String(opportunity.ville || '').trim()}
                          </span>
                        ) : null}
                        <span className="inline-flex items-center gap-1">
                          <CalendarDays className="h-4 w-4" />
                          Published: {formatDate(opportunity.date_publication)}
                        </span>
                        {opportunity.date_limite ? (
                          <span className="inline-flex items-center gap-1">
                            <CalendarDays className="h-4 w-4" />
                            Deadline: {formatDate(opportunity.date_limite)}
                          </span>
                        ) : null}
                      </div>

                      {(salaryLabel || experienceLabel || languagePreview.length > 0) && (
                        <div className="mb-3 flex flex-wrap gap-2">
                          {salaryLabel ? <Badge variant="outline">Salary: {salaryLabel}</Badge> : null}
                          {experienceLabel ? (
                            <Badge variant="outline">Experience: {experienceLabel}</Badge>
                          ) : null}
                          {languagePreview.length > 0 ? (
                            <Badge variant="outline">Languages: {languagePreview.join(', ')}</Badge>
                          ) : null}
                        </div>
                      )}

                      <p className="text-sm leading-6 text-neutral-700">{descriptionPreview}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 pt-4">
                    <p className="text-xs text-neutral-500">
                      {isUserAuthenticated
                        ? 'Open details for match explanation, similar opportunities, and actions.'
                        : 'Login to unlock AI match score and action workflow.'}
                    </p>

                    <div className="flex items-center gap-2">
                      {!isUserAuthenticated ? (
                        <Button asChild size="sm" variant="outline">
                          <Link to="/login">Login</Link>
                        </Button>
                      ) : null}
                      <Button asChild size="sm">
                        <Link to={`/opportunities/${opportunity.id}`}>View details</Link>
                      </Button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}

        <div className="mt-6 flex items-center justify-center gap-3">
          <Button
            variant="outline"
            onClick={handlePreviousPage}
            disabled={!hasPrevious || loading || isFetching}
          >
            Previous
          </Button>
          <span className="text-sm text-neutral-600">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            onClick={handleNextPage}
            disabled={!hasNext || loading || isFetching}
          >
            Next
          </Button>
        </div>
      </section>
    </div>
  );
}
