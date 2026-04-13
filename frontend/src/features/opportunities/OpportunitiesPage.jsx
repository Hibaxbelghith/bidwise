import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { Building2, CalendarDays, MapPin, Search } from 'lucide-react';

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

const formatDate = (value) => {
  if (!value) return 'N/A';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
};

const ANONYMOUS_ORGANIZATION_PATTERN = /entreprise\s+anonyme/i;

const formatOrganizationLabel = (opportunity) => {
  const organization = String(opportunity?.organisation_nom || '').trim();
  if (!organization || ANONYMOUS_ORGANIZATION_PATTERN.test(organization)) {
    return 'Entreprise confidentielle';
  }
  return organization;
};

const formatExperienceLabel = (opportunity) => {
  const experience = opportunity?.experience;
  if (!experience || typeof experience !== 'object') return '';

  const parseNumber = (value) => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return null;
    if (parsed <= 0) return null;
    return Math.floor(parsed);
  };

  const min = parseNumber(experience.min);
  const max = parseNumber(experience.max);

  if (min === null && max === null) return '';
  if (min !== null && max !== null) {
    return min === max ? `${min} years` : `${min}-${max} years`;
  }
  if (min !== null) return `${min}+ years`;
  return `Up to ${max} years`;
};

const getLanguagePreview = (opportunity) => {
  if (!Array.isArray(opportunity?.languages)) return [];

  const preview = [];
  const seen = new Set();
  for (const rawLanguage of opportunity.languages) {
    const language = String(rawLanguage || '').trim();
    if (!language || seen.has(language)) continue;
    seen.add(language);
    preview.push(language);
    if (preview.length >= 2) break;
  }

  return preview;
};

const getCompanyLogoUrl = (opportunity) => {
  const rawLogo =
    opportunity?.logo_url || opportunity?.organisation_logo || opportunity?.company_logo || '';
  return String(rawLogo).trim();
};

const truncate = (text, max = 200) => {
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

  return truncate(sourceText, 220);
};

const SkeletonOpportunityCard = ({ compact = false }) => (
  <article className="rounded-lg border border-neutral-200 bg-white p-5">
    <div className="animate-pulse space-y-4">
      <div className="flex items-start gap-4">
        <div className="h-12 w-12 shrink-0 rounded-lg bg-neutral-200" />
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
  <div className="mb-4 rounded-lg border border-neutral-200 bg-white px-4 py-3">
    <div className="animate-pulse space-y-2">
      <div className="h-2 w-28 rounded-full bg-neutral-200" />
      <div className="h-2 w-full rounded-full bg-neutral-100" />
    </div>
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
    <div className="min-h-screen bg-white">
      {!authLoading && !isAuthenticated && (
        <section className="border-b border-blue-100 bg-blue-50">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <p className="text-sm font-medium text-blue-900">
              Sign in to get personalized recommendations
            </p>
            <Button asChild size="sm" className="shrink-0">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </section>
      )}

      <section className="border-b border-neutral-200 bg-neutral-50">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="mb-6 text-3xl font-bold text-neutral-900">Browse Opportunities</h1>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
            <div className="relative lg:col-span-2">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
              <Input
                type="text"
                placeholder="Search title or description..."
                className="pl-9"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </div>

            <Input
              type="text"
              placeholder="Filter by city..."
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
          <p className="mt-3 text-xs text-neutral-500">
            Search updates automatically after a short delay to reduce unnecessary API calls.
          </p>
        </div>
      </section>

      <section ref={resultsSectionRef} className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-neutral-600">{count} opportunities found</p>
          <p className="text-sm text-neutral-600">
            Page {page} of {totalPages}
          </p>
        </div>

        {showFetchingSpinner && opportunities.length > 0 && <FetchingSkeletonBanner />}

        {loading && opportunities.length === 0 && (
          <div className="space-y-4">
            {[0, 1, 2].map((index) => (
              <SkeletonOpportunityCard key={index} />
            ))}
          </div>
        )}

        {!loading && error && opportunities.length === 0 && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            <p className="mb-3">{error}</p>
            <Button variant="outline" onClick={refetch}>
              Retry
            </Button>
          </div>
        )}

        {!loading && error && opportunities.length > 0 && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            {error}
          </div>
        )}

        {!loading && !error && opportunities.length === 0 && (
          <div className="rounded-lg border border-neutral-200 p-8 text-center">
            <h2 className="mb-2 text-lg font-semibold text-neutral-900">No opportunities found</h2>
            <p className="text-neutral-600">Try adjusting search terms or filters.</p>
            <div className="mt-4">
              <Button variant="outline" onClick={resetFilters}>
                Reset filters
              </Button>
            </div>
          </div>
        )}

        {!loading && opportunities.length > 0 && (
          <div className="space-y-4">
            {opportunities.map((opportunity) => {
              const salaryLabel = String(opportunity?.salary || '').trim();
              const experienceLabel = formatExperienceLabel(opportunity);
              const languagePreview = getLanguagePreview(opportunity);
              const companyLogoUrl = getCompanyLogoUrl(opportunity);
              const descriptionPreview = buildDescriptionPreview(opportunity);

              return (
                <article
                  key={opportunity.id}
                  className="rounded-lg border border-neutral-200 p-5 transition-colors hover:border-blue-300"
                >
                  <div className="mb-3 flex items-start gap-4">
                    <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-neutral-200 bg-white">
                      <Building2 className="h-5 w-5 text-neutral-400" />
                      {companyLogoUrl && (
                        <img
                          src={companyLogoUrl}
                          alt={`${formatOrganizationLabel(opportunity)} logo`}
                          className="absolute inset-0 h-full w-full rounded-lg bg-white object-contain"
                          loading="lazy"
                          onError={(event) => {
                            event.currentTarget.remove();
                          }}
                        />
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="mb-3 flex flex-wrap items-center gap-3">
                        <Link
                          to={`/opportunities/${opportunity.id}`}
                          className="text-xl font-semibold text-neutral-900 hover:text-blue-600"
                        >
                          {opportunity.titre || 'Untitled opportunity'}
                        </Link>
                        <Badge variant="secondary">
                          {TYPE_LABELS[opportunity.type_opportunite] || opportunity.type_opportunite || 'N/A'}
                        </Badge>
                        <Badge variant={opportunity.statut === 'ACTIVE' ? 'default' : 'outline'}>
                          {STATUS_LABELS[opportunity.statut] || opportunity.statut || 'N/A'}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="mb-3 flex flex-wrap gap-4 text-sm text-neutral-700">
                    <span className="inline-flex items-center gap-1">
                      <Building2 className="h-4 w-4" />
                      {formatOrganizationLabel(opportunity)}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      {String(opportunity.ville || '').trim() || 'N/A'}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <CalendarDays className="h-4 w-4" />
                      Published: {formatDate(opportunity.date_publication)}
                    </span>
                    {opportunity.date_limite && (
                      <span className="inline-flex items-center gap-1">
                        <CalendarDays className="h-4 w-4" />
                        Deadline: {formatDate(opportunity.date_limite)}
                      </span>
                    )}
                  </div>

                  {(salaryLabel || experienceLabel || languagePreview.length > 0) && (
                    <div className="mb-3 flex flex-wrap gap-2">
                      {salaryLabel && <Badge variant="outline">Salary: {salaryLabel}</Badge>}
                      {experienceLabel && <Badge variant="outline">Experience: {experienceLabel}</Badge>}
                      {languagePreview.length > 0 && (
                        <Badge variant="outline">Languages: {languagePreview.join(', ')}</Badge>
                      )}
                    </div>
                  )}

                  <p className="mb-4 text-neutral-700">{descriptionPreview}</p>

                  <div className="flex justify-end">
                    <Button asChild>
                      <Link to={`/opportunities/${opportunity.id}`}>View details</Link>
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        )}

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
