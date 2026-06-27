import { Search } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { Input } from '../../../../components/ui/input.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from '../../../../components/ui/select.jsx';

const Filters = ({
  searchDraft,
  source,
  status,
  sources,
  isLoading,
  isSourcesLoading,
  onSearchDraftChange,
  onSearchSubmit,
  onSourceChange,
  onStatusChange,
}) => (
  <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div>
      <h1 id="admin-opportunities-heading" className="text-3xl font-bold text-neutral-900">
        Opportunities
      </h1>
      <p className="mt-2 text-sm text-neutral-600">Review, filter, and remove imported opportunities.</p>
    </div>

    <form className="flex flex-col gap-3 sm:flex-row" onSubmit={onSearchSubmit}>
      <div className="relative sm:w-72">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" aria-hidden="true" />
        <Input
          type="search"
          value={searchDraft}
          onChange={(event) => onSearchDraftChange(event.target.value)}
          className="pl-9"
          placeholder="Search title"
          aria-label="Search by title"
        />
      </div>
      <Select value={source} onValueChange={onSourceChange}>
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
      <Select value={status} onValueChange={onStatusChange}>
        <SelectTrigger className="sm:w-48">
          <span />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="">All statuses</SelectItem>
          <SelectItem value="ACTIVE">Active</SelectItem>
          <SelectItem value="PENDING_REVIEW">Pending review</SelectItem>
          <SelectItem value="REJECTED">Rejected</SelectItem>
          <SelectItem value="SUSPENDUE">Suspended</SelectItem>
          <SelectItem value="FERMEE">Closed</SelectItem>
          <SelectItem value="EXPIREE">Expired</SelectItem>
          <SelectItem value="ARCHIVEE">Archived</SelectItem>
        </SelectContent>
      </Select>
      <Button type="submit" disabled={isLoading}>
        <Search className="h-4 w-4" aria-hidden="true" />
        Search
      </Button>
    </form>
  </div>
);

export default Filters;
