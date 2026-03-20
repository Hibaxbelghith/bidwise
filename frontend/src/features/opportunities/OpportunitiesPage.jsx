import { Link } from 'react-router-dom';
import { Building2, CalendarDays, Search } from 'lucide-react';

import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { useOpportunities } from './useOpportunities';

const TYPE_OPTIONS = [
  { value: 'EMPLOI', label: 'Job' },
  { value: 'STAGE', label: 'Internship' },
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

export function OpportunitiesBrowse() {
  const {
    opportunities,
    count,
    page,
    totalPages,
    hasNext,
    hasPrevious,
    loading,
    error,
    searchInput,
    setSearchInput,
    typeFilter,
    setTypeFilter,
    statusFilter,
    setStatusFilter,
    ordering,
    setOrdering,
    setPage,
    refetch,
  } = useOpportunities();

  return (
    <div className="min-h-screen bg-white">
      <section className="border-b border-neutral-200 bg-neutral-50">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="mb-6 text-3xl font-bold text-neutral-900">Browse Opportunities</h1>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="relative md:col-span-2">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
              <Input
                type="text"
                placeholder="Search title or description..."
                className="pl-9"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </div>

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

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-neutral-600">{count} opportunities found</p>
          <p className="text-sm text-neutral-600">
            Page {page} of {totalPages}
          </p>
        </div>

        {loading && (
          <div className="space-y-3">
            <div className="h-28 animate-pulse rounded-lg border border-neutral-200 bg-neutral-100" />
            <div className="h-28 animate-pulse rounded-lg border border-neutral-200 bg-neutral-100" />
            <div className="h-28 animate-pulse rounded-lg border border-neutral-200 bg-neutral-100" />
          </div>
        )}

        {!loading && error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            <p className="mb-3">{error}</p>
            <Button variant="outline" onClick={refetch}>
              Retry
            </Button>
          </div>
        )}

        {!loading && !error && opportunities.length === 0 && (
          <div className="rounded-lg border border-neutral-200 p-8 text-center">
            <h2 className="mb-2 text-lg font-semibold text-neutral-900">No opportunities found</h2>
            <p className="text-neutral-600">Try adjusting search terms or filters.</p>
          </div>
        )}

        {!loading && !error && opportunities.length > 0 && (
          <div className="space-y-4">
            {opportunities.map((opportunity) => (
              <article
                key={opportunity.id}
                className="rounded-lg border border-neutral-200 p-5 transition-colors hover:border-blue-300"
              >
                <div className="mb-3 flex flex-wrap items-center gap-3">
                  <Link
                    to={`/opportunities/${opportunity.id}`}
                    className="text-xl font-semibold text-neutral-900 hover:text-blue-600"
                  >
                    {opportunity.titre}
                  </Link>
                  <Badge variant="secondary">
                    {TYPE_LABELS[opportunity.type_opportunite] || opportunity.type_opportunite}
                  </Badge>
                  <Badge variant={opportunity.statut === 'ACTIVE' ? 'default' : 'outline'}>
                    {STATUS_LABELS[opportunity.statut] || opportunity.statut}
                  </Badge>
                </div>

                <div className="mb-3 flex flex-wrap gap-4 text-sm text-neutral-600">
                  <span className="inline-flex items-center gap-1">
                    <Building2 className="h-4 w-4" />
                    {opportunity.source?.nom || 'Unknown source'}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <CalendarDays className="h-4 w-4" />
                    Published: {formatDate(opportunity.date_publication)}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <CalendarDays className="h-4 w-4" />
                    Deadline: {formatDate(opportunity.date_limite)}
                  </span>
                </div>

                <p className="mb-4 text-neutral-700">{opportunity.description}</p>

                <div className="flex justify-end">
                  <Button asChild>
                    <Link to={`/opportunities/${opportunity.id}`}>View details</Link>
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}

        <div className="mt-6 flex items-center justify-center gap-3">
          <Button
            variant="outline"
            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            disabled={!hasPrevious || loading}
          >
            Previous
          </Button>
          <span className="text-sm text-neutral-600">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            onClick={() => setPage((prev) => prev + 1)}
            disabled={!hasNext || loading}
          >
            Next
          </Button>
        </div>
      </section>
    </div>
  );
}
