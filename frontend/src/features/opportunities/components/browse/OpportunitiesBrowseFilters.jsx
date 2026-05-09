import { BriefcaseBusiness, ChevronDown, MapPin, Search, SlidersHorizontal } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { Input } from '../../../../components/ui/input.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../../../components/ui/select.jsx';
import { STATUS_OPTIONS, TYPE_OPTIONS } from '../../constants/opportunityOptions.js';

const WORK_MODE_OPTIONS = [
  { value: 'REMOTE', label: 'Remote' },
  { value: 'HYBRID', label: 'Hybrid' },
  { value: 'ON_SITE', label: 'On site' },
];

const EXPERIENCE_OPTIONS = [
  { value: 'entry', label: 'Entry' },
  { value: 'junior', label: 'Junior' },
  { value: 'mid', label: 'Mid' },
  { value: 'senior', label: 'Senior' },
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

const FilterPill = ({ active, children, count, onClick }) => (
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
      <span className="truncate">{children}</span>
    </span>
    <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-semibold text-neutral-700">
      {count}
    </span>
  </button>
);

const FilterGroup = ({ title, children }) => (
  <div className="space-y-2">
    <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-700">{title}</h2>
    <div className="space-y-2">{children}</div>
  </div>
);

const SidebarFilters = ({
  opportunities,
  facets,
  sourceOptions,
  typeFilter,
  setTypeFilter,
  statusFilter,
  setStatusFilter,
  sourceFilter,
  setSourceFilter,
  workModeFilter,
  setWorkModeFilter,
  experienceFilter,
  setExperienceFilter,
}) => {
  const typeCounts = Object.keys(facets?.types || {}).length
    ? facetCountsByKey(facets.types)
    : countBy(opportunities, (item) => item?.type_opportunite);
  const statusCounts = Object.keys(facets?.statuses || {}).length
    ? facetCountsByKey(facets.statuses)
    : countBy(opportunities, (item) => item?.statut);
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
      <FilterGroup title="Opportunity types">
        {TYPE_OPTIONS.map((option) => (
          <FilterPill
            key={option.value}
            active={typeFilter === option.value}
            count={typeCounts[option.value] || 0}
            onClick={() => handleTypeClick(option.value)}
          >
            {option.label}
          </FilterPill>
        ))}
      </FilterGroup>

      {showRoleFilters ? (
        <>
          <FilterGroup title="Work mode">
            {WORK_MODE_OPTIONS.map((option) => (
              <FilterPill
                key={option.value}
                active={workModeFilter === option.value}
                count={workModeCounts[option.value] || 0}
                onClick={() => setWorkModeFilter(workModeFilter === option.value ? '' : option.value)}
              >
                {option.label}
              </FilterPill>
            ))}
          </FilterGroup>

          <FilterGroup title="Experience">
            {EXPERIENCE_OPTIONS.map((option) => (
              <FilterPill
                key={option.value}
                active={experienceFilter === option.value}
                count={experienceCounts[option.value] || 0}
                onClick={() => setExperienceFilter(experienceFilter === option.value ? '' : option.value)}
              >
                {option.label}
              </FilterPill>
            ))}
          </FilterGroup>
        </>
      ) : null}

      <FilterGroup title="Scraping sources">
        {sourceOptions.length > 0 ? (
          sourceOptions.map((source) => (
            <FilterPill
              key={source.id}
              active={sourceFilter === String(source.id)}
              count={sourceCounts[String(source.id)] || 0}
              onClick={() => setSourceFilter(sourceFilter === String(source.id) ? '' : String(source.id))}
            >
              {source.nom}
            </FilterPill>
          ))
        ) : (
          <p className="rounded-md border border-dashed border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-700">
            Sources will appear as soon as the index responds.
          </p>
        )}
      </FilterGroup>

      <FilterGroup title="Status">
        {STATUS_OPTIONS.map((option) => (
          <FilterPill
            key={option.value}
            active={statusFilter === option.value}
            count={statusCounts[option.value] || 0}
            onClick={() => setStatusFilter(statusFilter === option.value ? '' : option.value)}
          >
            {option.label}
          </FilterPill>
        ))}
      </FilterGroup>
    </div>
  );
};

const OpportunitiesBrowseFilters = ({
  variant = 'toolbar',
  hasActiveFilters,
  searchInput,
  setSearchInput,
  cityFilter,
  setCityFilter,
  cityOptions,
  typeFilter,
  setTypeFilter,
  statusFilter,
  setStatusFilter,
  sourceFilter,
  setSourceFilter,
  sourceOptions,
  facets,
  workModeFilter,
  setWorkModeFilter,
  experienceFilter,
  setExperienceFilter,
  opportunities,
  resetFilters,
}) => {
  const sidebarProps = {
    opportunities,
    facets,
    sourceOptions,
    typeFilter,
    setTypeFilter,
    statusFilter,
    setStatusFilter,
    sourceFilter,
    setSourceFilter,
    workModeFilter,
    setWorkModeFilter,
    experienceFilter,
    setExperienceFilter,
  };

  if (variant === 'sidebar') {
    return (
      <aside className="hidden lg:block">
        <div className="sticky top-24 rounded-md border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-950">Filters</h2>
            {hasActiveFilters ? (
              <button
                type="button"
                onClick={resetFilters}
                className="text-xs font-semibold text-blue-700 hover:text-blue-900"
              >
                Reset all
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
              placeholder="Search roles, skills or companies..."
              className="h-11 bg-white pl-9 text-neutral-900 placeholder:text-neutral-500"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>

          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
            <Input
              type="text"
              placeholder="Location"
              value={cityFilter}
              list="city-filter-options"
              className="h-11 bg-white pl-9 text-neutral-900 placeholder:text-neutral-500"
              onChange={(event) => setCityFilter(event.target.value)}
            />
            <datalist id="city-filter-options">
              {cityOptions.map((city) => (
                <option key={city} value={city} />
              ))}
            </datalist>
          </div>

          <Select
            value={typeFilter || 'all'}
            onValueChange={(value) => {
              const nextValue = value === 'all' ? '' : value;
              setTypeFilter(nextValue);
              if (!['EMPLOI', 'STAGE'].includes(nextValue)) {
                setWorkModeFilter('');
                setExperienceFilter('');
              }
            }}
          >
            <SelectTrigger className="h-11 bg-white">
              <BriefcaseBusiness className="h-4 w-4 text-neutral-500" />
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

          {hasActiveFilters ? (
            <Button size="lg" variant="outline" onClick={resetFilters}>
              Reset
            </Button>
          ) : null}
        </div>

        <details className="mt-3 rounded-md border border-neutral-200 bg-neutral-50 p-3 lg:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-semibold text-neutral-900">
            <span className="inline-flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4" />
              More filters
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
