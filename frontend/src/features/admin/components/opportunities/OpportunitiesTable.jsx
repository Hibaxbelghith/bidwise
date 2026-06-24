import { ArrowDown, ArrowUp, ArrowUpDown, Eye, Trash2 } from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../../../components/ui/table.jsx';
import {
  formatDate,
  originClassName,
  originLabel,
  statusClassName,
  statusLabel,
  typeLabel,
} from './opportunity.Utils.js';

const ariaSortFor = (ordering, field) => {
  if (ordering === field) return 'ascending';
  if (ordering === `-${field}`) return 'descending';
  return 'none';
};

const sortIconFor = (ordering, field) => {
  if (ordering === field) return ArrowUp;
  if (ordering === `-${field}`) return ArrowDown;
  return ArrowUpDown;
};

const SortableHeader = ({ children, field, ordering, onToggleOrdering, className = '' }) => {
  const Icon = sortIconFor(ordering, field);

  return (
    <TableHead className={className} aria-sort={ariaSortFor(ordering, field)}>
      <button
        type="button"
        className="inline-flex items-center gap-1 text-sm font-medium text-neutral-700 hover:text-neutral-950"
        onClick={() => onToggleOrdering(field)}
      >
        {children}
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </TableHead>
  );
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

const OpportunitiesTable = ({
  opportunities,
  count,
  isSourcesLoading,
  isLoading,
  isInitialLoading,
  isRefreshing,
  ordering,
  deletingId,
  onToggleOrdering,
  onViewOpportunity,
  onDeleteOpportunity,
}) => (
  <Card className="overflow-hidden">
    <CardHeader className="flex flex-col gap-2 border-b border-neutral-200 sm:flex-row sm:items-center sm:justify-between">
      <CardTitle className="text-base">Opportunity list</CardTitle>
      <div className="flex items-center gap-3 text-sm text-neutral-500">
        {isSourcesLoading ? <div className="h-4 w-16 rounded bg-neutral-200 animate-pulse" /> : null}
        <span>{count} total</span>
      </div>
    </CardHeader>
    <CardContent className="p-0">
      <Table>
        <TableHeader>
          <TableRow className="bg-neutral-50">
            <SortableHeader
              field="title"
              ordering={ordering}
              onToggleOrdering={onToggleOrdering}
              className="px-4 py-3"
            >
              Title
            </SortableHeader>
            <SortableHeader
              field="type"
              ordering={ordering}
              onToggleOrdering={onToggleOrdering}
              className="px-4 py-3"
            >
              Type
            </SortableHeader>
            <SortableHeader
              field="source"
              ordering={ordering}
              onToggleOrdering={onToggleOrdering}
              className="px-4 py-3"
            >
              Origin
            </SortableHeader>
            <SortableHeader
              field="published_at"
              ordering={ordering}
              onToggleOrdering={onToggleOrdering}
              className="px-4 py-3"
            >
              Published
            </SortableHeader>
            <SortableHeader
              field="status"
              ordering={ordering}
              onToggleOrdering={onToggleOrdering}
              className="px-4 py-3"
            >
              Status
            </SortableHeader>
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
              <TableCell colSpan={6} className="px-4 py-10 text-center text-neutral-500">
                No opportunities found.
              </TableCell>
            </TableRow>
          ) : (
            opportunities.map((opportunity) => (
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
                  <Badge variant="secondary">{typeLabel(opportunity.type)}</Badge>
                </TableCell>
                <TableCell className="px-4 py-3">
                  <Badge variant="outline" className={originClassName(opportunity)}>
                    {originLabel(opportunity)}
                  </Badge>
                </TableCell>
                <TableCell className="px-4 py-3 text-neutral-600">
                  {formatDate(opportunity.published_at || opportunity.created_at)}
                </TableCell>
                <TableCell className="px-4 py-3">
                  <Badge variant="outline" className={statusClassName(opportunity.status)}>
                    {statusLabel(opportunity.status)}
                  </Badge>
                  {opportunity.moderation_summary?.final_status === 'PENDING_REVIEW' ? (
                    <p className="mt-1 text-xs font-medium text-blue-700">Review needed</p>
                  ) : null}
                </TableCell>
                <TableCell className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={isLoading}
                      onClick={() => onViewOpportunity(opportunity)}
                    >
                      <Eye className="h-4 w-4" aria-hidden="true" />
                      View
                    </Button>
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      disabled={deletingId === opportunity.id || isLoading}
                      onClick={() => onDeleteOpportunity(opportunity)}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                      {deletingId === opportunity.id ? 'Deleting' : 'Delete'}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </CardContent>
  </Card>
);

export default OpportunitiesTable;
