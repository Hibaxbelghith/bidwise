import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileUser, Users } from 'lucide-react';

import { Badge } from '../../../components/ui/badge.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../../components/ui/table.jsx';
import OrganizationOpportunitiesPagination from './OrganizationOpportunitiesPagination.jsx';
import OrganizationOpportunityActionsMenu from './OrganizationOpportunityActionsMenu.jsx';
import {
  ORGANIZATION_OPPORTUNITY_EDITABLE_STATUSES,
  OrganizationOpportunityStatusSelect,
} from './OrganizationOpportunityStatus.jsx';
import {
  ORGANIZATION_OPPORTUNITY_TYPE_LABELS,
  formatOrganizationOpportunityDate,
} from '../utils/organizationOpportunityFormatters.js';

const PAGE_SIZE = 10;

const OrganizationOpportunitiesTable = ({ opportunities, statusActionId, onStatusAction }) => {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(Math.ceil(opportunities.length / PAGE_SIZE), 1);
  const visibleOpportunities = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return opportunities.slice(start, start + PAGE_SIZE);
  }, [opportunities, page]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  return (
    <div className="rounded-lg border border-neutral-200 bg-white">
      <Table className="table-fixed" containerClassName="overflow-visible">
        <TableHeader>
          <TableRow className="bg-neutral-50">
            <TableHead className="w-[36%] px-4">Opportunity</TableHead>
            <TableHead className="hidden w-[15%] md:table-cell">Type</TableHead>
            <TableHead className="w-[190px]">Status</TableHead>
            <TableHead className="hidden w-[15%] lg:table-cell">Published</TableHead>
            <TableHead className="hidden w-[190px] sm:table-cell">Applications</TableHead>
            <TableHead className="w-14 text-right">
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {visibleOpportunities.map((opportunity) => (
            <TableRow key={opportunity.id}>
              <TableCell className="px-4 py-3 align-top whitespace-normal">
                <p className="line-clamp-2 break-words font-medium leading-5 text-neutral-950">
                  {opportunity.title}
                </p>
                <p className="mt-1 truncate text-xs text-neutral-500">
                  {opportunity.location || 'Location not set'}
                </p>
              </TableCell>
              <TableCell className="hidden md:table-cell">
                <Badge variant="secondary">
                  {ORGANIZATION_OPPORTUNITY_TYPE_LABELS[opportunity.type] || opportunity.type}
                </Badge>
              </TableCell>
              <TableCell>
                <OrganizationOpportunityStatusSelect
                  opportunity={opportunity}
                  disabled={statusActionId === opportunity.id}
                  onAction={onStatusAction}
                />
              </TableCell>
              <TableCell className="hidden text-neutral-600 lg:table-cell">
                {formatOrganizationOpportunityDate(opportunity.published_at)}
              </TableCell>
              <TableCell className="hidden sm:table-cell">
                <div className="grid grid-cols-2 gap-3" aria-label="Application counts">
                  <Link
                    to={`/organization/applications?filter=all`}
                    className="min-w-0 block hover:opacity-75 transition-opacity"
                  >
                    <div className="flex items-center gap-1.5">
                      <Users className="h-4 w-4 shrink-0 text-neutral-700" aria-hidden="true" />
                      <span className="font-semibold text-blue-700">
                        {Number(opportunity.applications_count || 0)} total
                      </span>
                    </div>
                  </Link>
                  {Number(opportunity.new_applications_count || 0) > 0 && (
                    <Link
                      to={`/organization/applications?filter=new`}
                      className="min-w-0 block hover:opacity-75 transition-opacity"
                    >
                      <div className="flex items-center gap-1.5">
                        <FileUser className="h-4 w-4 shrink-0 text-neutral-700" aria-hidden="true" />
                        <span className="font-semibold text-blue-700">
                          {Number(opportunity.new_applications_count || 0)} new
                        </span>
                      </div>
                    </Link>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-right">
                <OrganizationOpportunityActionsMenu
                  opportunity={opportunity}
                  editable={ORGANIZATION_OPPORTUNITY_EDITABLE_STATUSES.has(opportunity.status)}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <OrganizationOpportunitiesPagination
        page={page}
        pageSize={PAGE_SIZE}
        total={opportunities.length}
        onPageChange={setPage}
      />
    </div>
  );
};

export default OrganizationOpportunitiesTable;
