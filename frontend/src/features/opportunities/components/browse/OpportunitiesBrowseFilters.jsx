import { Search } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { Input } from '../../../../components/ui/input.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../../../components/ui/select.jsx';
import {
  ORDER_OPTIONS,
  STATUS_OPTIONS,
  TYPE_OPTIONS,
} from '../../constants/opportunityOptions.js';

const OpportunitiesBrowseFilters = ({
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
  ordering,
  setOrdering,
  resetFilters,
}) => (
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
);

export default OpportunitiesBrowseFilters;
