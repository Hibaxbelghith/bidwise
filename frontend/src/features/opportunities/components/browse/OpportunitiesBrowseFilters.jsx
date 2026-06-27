import { useMemo, useState } from 'react';

import { CalendarDays, ChevronDown, MapPin, Search, SlidersHorizontal } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { Input } from '../../../../components/ui/input.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../../../components/ui/select.jsx';
import { TYPE_OPTIONS } from '../../constants/opportunityOptions.js';

const WORK_MODE_OPTIONS = [
  { value: 'REMOTE', labelKey: 'opportunities.filters.remote' },
  { value: 'HYBRID', labelKey: 'opportunities.filters.hybrid' },
  { value: 'ON_SITE', labelKey: 'opportunities.filters.onSite' },
];

const EXPERIENCE_OPTIONS = [
  { value: 'entry', labelKey: 'opportunities.filters.entry' },
  { value: 'junior', labelKey: 'opportunities.filters.junior' },
  { value: 'mid', labelKey: 'opportunities.filters.mid' },
  { value: 'senior', labelKey: 'opportunities.filters.senior' },
];

const DATE_POSTED_OPTIONS = [
  { value: 'all', labelKey: 'opportunities.filters.anyTime' },
  { value: 'day', labelKey: 'opportunities.filters.lastDay' },
  { value: '3days', labelKey: 'opportunities.filters.last3Days' },
  { value: 'week', labelKey: 'opportunities.filters.lastWeek' },
  { value: '2weeks', labelKey: 'opportunities.filters.last2Weeks' },
  { value: 'month', labelKey: 'opportunities.filters.lastMonth' },
];

const DEADLINE_WINDOW_OPTIONS = [
  { value: 'all', labelKey: 'opportunities.filters.anyDeadline' },
  { value: 'week', labelKey: 'opportunities.filters.thisWeek' },
  { value: 'month', labelKey: 'opportunities.filters.thisMonth' },
];

const TYPE_LABEL_KEYS = {
  EMPLOI: 'opportunities.filters.typeJob',
  STAGE: 'opportunities.filters.typeInternship',
  SAISONNIER: 'opportunities.filters.typeSeasonal',
  PROJET: 'opportunities.filters.typeTender',
};

const SOURCE_LOGOS = [
  {
    match: /keejob/i,
    src: '/logos_sites_sources/keejob_logo.jpg',
    alt: 'Keejob logo',
  },
  {
    match: /linkedin/i,
    src: '/logos_sites_sources/logos_opportunities/LinkedIn_icon.svg.webp',
    alt: 'LinkedIn logo',
  },
  {
    match: /emploi\s*tunisie|emploitunisie/i,
    src: '/logos_sites_sources/emploiTunisie.png',
    alt: 'EmploiTunisie logo',
  },
  {
    match: /bidwise/i,
    src: '/BidWise Icon.png',
    alt: 'BidWise logo',
  },
  {
    match: /march[eé]s?\s*publics|haicop|tunips|tuneps/i,
    src: '/logos_sites_sources/HAICOP.png',
    alt: 'Marches publics logo',
  },
];

const countBy = (items, getKey) =>
  (items || []).reduce((accumulator, item) => {
    const key = String(getKey(item) || '').trim();
    if (!key) return accumulator;
    accumulator[key] = (accumulator[key] || 0) + 1;
    return accumulator;
  }, {});

const facetCountsByKey = (items = []) =>
  items.reduce((accumulator, item) => {
    const key = String(item?.key || '').trim();
    if (key) accumulator[key] = Number(item.count) || 0;
    if (item?.id != null) accumulator[String(item.id)] = Number(item.count) || 0;
    return accumulator;
  }, {});

const facetOptionsByKey = (items = []) =>
  items
    .map((item) => ({
      key: String(item?.key || '').trim(),
      count: Number(item?.count) || 0,
    }))
    .filter((item) => item.key);

const inferWorkMode = (opportunity) => {
  const normalized = String(opportunity?.normalized_work_mode || '').trim().toUpperCase();
  if (normalized && normalized !== 'UNSPECIFIED') return normalized;

  const text = `${opportunity?.availability || ''} ${opportunity?.description || ''}`.toLowerCase();
  if (text.includes('hybrid') || text.includes('hybride')) return 'HYBRID';
  if (text.includes('remote') || text.includes('distance') || text.includes('teletravail')) return 'REMOTE';
  if (text.includes('on site') || text.includes('onsite') || text.includes('presentiel')) return 'ON_SITE';
  return '';
};

const inferExperienceLevel = (opportunity) => {
  const min = Number(opportunity?.experience?.min);
  const max = Number(opportunity?.experience?.max);
  const floor = Number.isFinite(min) ? min : Number.isFinite(max) ? max : null;

  if (floor === null) return '';
  if (floor <= 1) return 'entry';
  if (floor <= 2) return 'junior';
  if (floor <= 5) return 'mid';
  return 'senior';
};

const getSourceLogo = (sourceName) => {
  const normalized = String(sourceName || '').trim();
  if (!normalized) return null;
  return SOURCE_LOGOS.find((logo) => logo.match.test(normalized)) || null;
};

const SourceLogo = ({ sourceName }) => {
  const logo = getSourceLogo(sourceName);
  const fallbackInitial = String(sourceName || '?').trim().charAt(0).toUpperCase() || '?';
  const [imageFailed, setImageFailed] = useState(false);

  const shouldShowImage = Boolean(logo) && !imageFailed;

  return (
    <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center overflow-hidden rounded bg-white ring-1 ring-neutral-200">
      {shouldShowImage ? (
        <img
          src={logo.src}
          alt={logo.alt}
          className="h-full w-full object-contain"
          loading="lazy"
          onError={(event) => {
            event.currentTarget.style.display = 'none';
            setImageFailed(true);
          }}
        />
      ) : (
        <span className="text-[10px] font-bold text-neutral-500">{fallbackInitial}</span>
      )}
    </span>
  );
};

const FilterPill = ({ active, children, count, leadingVisual = null, onClick }) => (
  <button
    type="button"
    aria-pressed={active}
    onClick={onClick}
    className={[
      'flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2 text-left text-sm font-medium transition-colors',
      active
        ? 'border-blue-600 bg-blue-50 text-blue-800'
        : 'border-neutral-200 bg-white text-neutral-800 hover:border-neutral-300 hover:bg-neutral-50',
    ].join(' ')}
  >
    <span className="inline-flex min-w-0 items-center gap-2">
      <span
        className={[
          'h-3 w-3 rounded border',
          active ? 'border-blue-600 bg-blue-600' : 'border-neutral-300 bg-white',
        ].join(' ')}
      />
      {leadingVisual}
      <span className="truncate">{children}</span>
    </span>
    <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-semibold text-neutral-700">
      {count}
    </span>
  </button>
);

const FilterPillSkeleton = () => (
  <div className="flex w-full items-center justify-between gap-3 rounded-md border border-neutral-200 bg-white px-3 py-2">
    <span className="inline-flex min-w-0 items-center gap-2">
      <span className="h-3 w-3 rounded border border-neutral-200 bg-neutral-100" />
      <span className="h-4 w-24 animate-pulse rounded bg-neutral-100" />
    </span>
    <span className="h-5 w-8 animate-pulse rounded-full bg-neutral-100" />
  </div>
);

const FilterGroup = ({ title, children }) => (
  <div className="space-y-2">
    <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-700">{title}</h2>
    <div className="space-y-2">{children}</div>
  </div>
);

const LocationFilterInput = ({ cityFilter, locationOptions, setCityFilter }) => {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const normalizedFilter = cityFilter.trim().toLowerCase();
  const visibleOptions = useMemo(() => {
    if (!normalizedFilter) return locationOptions;
    return locationOptions.filter((location) => location.key.toLowerCase().includes(normalizedFilter));
  }, [locationOptions, normalizedFilter]);

  return (
    <div className="relative">
      <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
      <Input
        type="text"
        placeholder={t('opportunities.filters.location')}
        value={cityFilter}
        className="h-11 bg-white pl-9 pr-9 text-neutral-900 placeholder:text-neutral-500"
        autoComplete="off"
        aria-expanded={isOpen}
        aria-controls="city-filter-options"
        onFocus={() => setIsOpen(true)}
        onChange={(event) => {
          setCityFilter(event.target.value);
          setIsOpen(true);
        }}
        onBlur={() => {
          window.setTimeout(() => setIsOpen(false), 120);
        }}
      />
      <button
        type="button"
        aria-label={t('opportunities.filters.toggleLocationOptions')}
        className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800"
        onMouseDown={(event) => {
          event.preventDefault();
          setIsOpen((value) => !value);
        }}
      >
        <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && locationOptions.length > 0 ? (
        <div
          id="city-filter-options"
          role="listbox"
          className="absolute left-0 right-0 top-[calc(100%+0.375rem)] z-40 max-h-72 overflow-y-auto rounded-md border border-neutral-200 bg-white py-1 shadow-lg"
        >
          {visibleOptions.length > 0 ? (
            visibleOptions.map((location) => (
              <button
                key={location.key}
                type="button"
                role="option"
                aria-selected={cityFilter === location.key}
                className={[
                  'flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm transition-colors',
                  cityFilter === location.key
                    ? 'bg-blue-50 text-blue-800'
                    : 'text-neutral-800 hover:bg-neutral-50',
                ].join(' ')}
                onMouseDown={(event) => {
                  event.preventDefault();
                  setCityFilter(location.key);
                  setIsOpen(false);
                }}
              >
                <span className="truncate font-medium">{location.key}</span>
                {location.count ? (
                  <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-semibold text-neutral-600">
                    {location.count}
                  </span>
                ) : null}
              </button>
            ))
          ) : (
            <p className="px-3 py-2 text-sm text-neutral-500">{t('opportunities.filters.noLocationsFound')}</p>
          )}
        </div>
      ) : null}
    </div>
  );
};

const SidebarFilters = ({
  loading,
  opportunities,
  facets,
  sourceOptions,
  tenderOnly = false,
  typeFilter,
  setTypeFilter,
  sourceFilter,
  setSourceFilter,
  workModeFilter,
  setWorkModeFilter,
  experienceFilter,
  setExperienceFilter,
}) => {
  const { t } = useLanguage();
  const typeCounts = Object.keys(facets?.types || {}).length
    ? facetCountsByKey(facets.types)
    : countBy(opportunities, (item) => item?.type_opportunite);
  const showTypeSkeleton = loading && !Object.keys(facets?.types || {}).length;
  const workModeCounts = Object.keys(facets?.work_modes || {}).length
    ? facetCountsByKey(facets.work_modes)
    : countBy(opportunities, inferWorkMode);
  const experienceCounts = Object.keys(facets?.experience_levels || {}).length
    ? facetCountsByKey(facets.experience_levels)
    : countBy(opportunities, inferExperienceLevel);
  const sourceCounts = Object.keys(facets?.sources || {}).length
    ? facetCountsByKey(facets.sources)
    : countBy(opportunities, (item) => item?.source?.id);
  const showRoleFilters = ['EMPLOI', 'STAGE'].includes(typeFilter);

  const handleTypeClick = (value) => {
    const nextValue = typeFilter === value ? '' : value;
    setTypeFilter(nextValue);

    if (!['EMPLOI', 'STAGE'].includes(nextValue)) {
      setWorkModeFilter('');
      setExperienceFilter('');
    }
  };

  return (
    <div className="space-y-6">
      <FilterGroup title={t('opportunities.filters.opportunityTypes')}>
        {tenderOnly ? (
          <FilterPill active count={typeCounts.PROJET || 0} onClick={() => {}}>
            {t('opportunities.filters.callsForTender')}
          </FilterPill>
        ) : showTypeSkeleton ? (
          TYPE_OPTIONS.map((option) => <FilterPillSkeleton key={option.value} />)
        ) : (
          TYPE_OPTIONS.map((option) => (
            <FilterPill
              key={option.value}
              active={typeFilter === option.value}
              count={typeCounts[option.value] || 0}
              onClick={() => handleTypeClick(option.value)}
            >
              {t(TYPE_LABEL_KEYS[option.value] || option.label)}
            </FilterPill>
          ))
        )}
      </FilterGroup>

      {showRoleFilters ? (
        <>
          <FilterGroup title={t('opportunities.filters.workMode')}>
            {WORK_MODE_OPTIONS.map((option) => (
              <FilterPill
                key={option.value}
                active={workModeFilter === option.value}
                count={workModeCounts[option.value] || 0}
                onClick={() => setWorkModeFilter(workModeFilter === option.value ? '' : option.value)}
              >
                {t(option.labelKey)}
              </FilterPill>
            ))}
          </FilterGroup>

          <FilterGroup title={t('opportunities.filters.experience')}>
            {EXPERIENCE_OPTIONS.map((option) => (
              <FilterPill
                key={option.value}
                active={experienceFilter === option.value}
                count={experienceCounts[option.value] || 0}
                onClick={() => setExperienceFilter(experienceFilter === option.value ? '' : option.value)}
              >
                {t(option.labelKey)}
              </FilterPill>
            ))}
          </FilterGroup>
        </>
      ) : null}

      {!tenderOnly ? (
      <FilterGroup title={t('opportunities.filters.sources')}>
        {sourceOptions.length > 0 ? (
          sourceOptions.map((source) => (
            <FilterPill
              key={source.id}
              active={sourceFilter === String(source.id)}
              count={sourceCounts[String(source.id)] || 0}
              leadingVisual={<SourceLogo sourceName={source.nom} />}
              onClick={() => setSourceFilter(sourceFilter === String(source.id) ? '' : String(source.id))}
            >
              {source.nom}
            </FilterPill>
          ))
        ) : (
          <>
            <FilterPillSkeleton />
            <FilterPillSkeleton />
            <FilterPillSkeleton />
          </>
        )}
      </FilterGroup>
      ) : null}
    </div>
  );
};

const OpportunitiesBrowseFilters = ({
  variant = 'toolbar',
  loading,
  hasActiveFilters,
  searchInput,
  setSearchInput,
  cityFilter,
  setCityFilter,
  cityOptions,
  typeFilter,
  setTypeFilter,
  sourceFilter,
  setSourceFilter,
  sourceOptions,
  facets,
  workModeFilter,
  setWorkModeFilter,
  experienceFilter,
  setExperienceFilter,
  datePostedFilter,
  setDatePostedFilter,
  opportunities,
  resetFilters,
  tenderOnly = false,
}) => {
  const { t } = useLanguage();
  const sidebarProps = {
    loading,
    opportunities,
    facets,
    sourceOptions,
    tenderOnly,
    typeFilter,
    setTypeFilter,
    sourceFilter,
    setSourceFilter,
    workModeFilter,
    setWorkModeFilter,
    experienceFilter,
    setExperienceFilter,
  };
  const facetLocationOptions = facetOptionsByKey(facets?.locations);
  const locationOptions = facetLocationOptions.length
    ? facetLocationOptions
    : cityOptions.map((city) => ({ key: city, count: 0 }));
  const dateFilterOptions = tenderOnly ? DEADLINE_WINDOW_OPTIONS : DATE_POSTED_OPTIONS;
  const dateFilterPlaceholder = tenderOnly ? t('opportunities.filters.deadline') : t('opportunities.filters.datePosted');
  const searchPlaceholder = tenderOnly
    ? t('opportunities.filters.searchTenders')
    : t('opportunities.filters.searchGeneral');

  if (variant === 'sidebar') {
    return (
      <aside className="hidden lg:block">
        <div className="sticky top-24 rounded-md border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-950">{t('opportunities.filters.filters')}</h2>
            {hasActiveFilters ? (
              <button
                type="button"
                onClick={resetFilters}
                className="text-xs font-semibold text-blue-700 hover:text-blue-900"
              >
                {t('opportunities.filters.resetAll')}
              </button>
            ) : null}
          </div>
          <SidebarFilters {...sidebarProps} />
        </div>
      </aside>
    );
  }

  return (
    <section className="sticky top-0 z-20 border-b border-neutral-200 bg-white/95 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_220px_auto] lg:items-center">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
            <Input
              type="text"
              placeholder={searchPlaceholder}
              className="h-11 bg-white pl-9 text-neutral-900 placeholder:text-neutral-500"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>

          <LocationFilterInput
            cityFilter={cityFilter}
            locationOptions={locationOptions}
            setCityFilter={setCityFilter}
          />

          <Select
            value={datePostedFilter || ''}
            onValueChange={(value) => {
              setDatePostedFilter(value === 'all' ? '' : value);
            }}
          >
          <SelectTrigger className="h-11 bg-white">
              <CalendarDays className="h-4 w-4 text-neutral-500" />
              <SelectValue placeholder={dateFilterPlaceholder} />
            </SelectTrigger>
            <SelectContent>
              {dateFilterOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {t(option.labelKey)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {hasActiveFilters ? (
            <Button size="lg" variant="outline" onClick={resetFilters}>
              {t('opportunities.filters.reset')}
            </Button>
          ) : null}
        </div>

        <details className="mt-3 rounded-md border border-neutral-200 bg-neutral-50 p-3 lg:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-semibold text-neutral-900">
            <span className="inline-flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4" />
              {t('opportunities.filters.moreFilters')}
            </span>
            <ChevronDown className="h-4 w-4" />
          </summary>
          <div className="mt-4">
            <SidebarFilters {...sidebarProps} />
          </div>
        </details>
      </div>
    </section>
  );
};

export default OpportunitiesBrowseFilters;
