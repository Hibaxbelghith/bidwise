import { Link } from 'react-router-dom';
import { FilePlus2 } from 'lucide-react';
import { Button } from '../../../components/ui/button.jsx';
import OrganizationOpportunitiesTable from './OrganizationOpportunitiesTable.jsx';
import OpportunitiesStats from './OpportunitiesStats.jsx';

const OpportunitiesContent = ({
  isLoading,
  filteredOpportunities,
  opportunities,
  stats,
  statusActionId,
  onStatusAction,
  onResetFilters,
}) => {
  if (isLoading) {
    return (
      <div className="flex min-h-[560px] flex-col items-center justify-center px-6 py-12 text-center">
        <div className="flex items-center gap-3 rounded-xl border border-neutral-200 bg-white px-5 py-4 text-sm font-semibold text-neutral-600 shadow-sm">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue-700" />
          Loading your published opportunities
        </div>
      </div>
    );
  }

  if (filteredOpportunities.length > 0) {
    return (
      <div className="px-5 py-5">
        <OpportunitiesStats
          total={stats.total}
          active={stats.active}
          applications={stats.applications}
        />
        <OrganizationOpportunitiesTable
          opportunities={filteredOpportunities}
          statusActionId={statusActionId}
          onStatusAction={onStatusAction}
        />
      </div>
    );
  }

  if (opportunities.length > 0) {
    return (
      <div className="flex min-h-[560px] flex-col items-center justify-center px-6 py-12 text-center">
        <div className="mb-4 rounded-lg border border-neutral-200 bg-neutral-50 p-6">
          <p className="text-sm text-neutral-600">
            No opportunities match the selected filters.
          </p>
          <button
            onClick={onResetFilters}
            className="mt-3 text-sm text-blue-700 font-semibold hover:text-blue-800"
          >
            Reset all filters
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[560px] flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-8 flex h-44 w-72 items-center justify-center rounded-[2rem] bg-[#f6d0a5]">
        <div className="relative h-28 w-44">
          <div className="absolute bottom-0 left-4 h-16 w-32 rounded-t-[4rem] bg-[#eaa24d]" />
          <div className="absolute left-12 top-2 h-16 w-16 rounded-full bg-[#2d2d2d]" />
          <div className="absolute left-24 top-14 h-14 w-24 rounded-xl bg-white shadow-sm" />
          <div className="absolute right-0 top-0 h-16 w-16 rounded-full bg-[#79b7a3]" />
          <div className="absolute right-5 top-5 h-12 w-8 rounded-t-full bg-[#4a987d]" />
        </div>
      </div>
      <h2 className="max-w-4xl text-2xl font-semibold text-neutral-950">
        Publish your first opportunity and start receiving qualified applications.
      </h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">
        Create a job, internship, or seasonal role directly on BidWise. Your organization
        will be able to manage opportunities and track applications from this workspace.
      </p>
      <Button asChild className="mt-8 h-12 rounded-xl bg-blue-700 px-5 text-white hover:bg-blue-800">
        <Link to="/organization/post">
          <FilePlus2 className="h-4 w-4" aria-hidden="true" />
          Publish an opportunity
        </Link>
      </Button>
    </div>
  );
};

export default OpportunitiesContent;
