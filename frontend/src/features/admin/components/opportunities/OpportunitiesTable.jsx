import { Eye, Trash2 } from 'lucide-react';

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
import { formatDate, getSourceName, sourceClassName, statusClassName } from './opportunity.Utils.js';

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

const OpportunitiesTable = ({
  opportunities,
  count,
  isSourcesLoading,
  isLoading,
  isInitialLoading,
  isRefreshing,
  deletingId,
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
