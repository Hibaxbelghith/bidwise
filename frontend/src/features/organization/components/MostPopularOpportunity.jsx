import { useMemo } from 'react';
import { Star } from 'lucide-react';

const MostPopularOpportunity = ({ opportunities, applicationsData }) => {
  const mostPopular = useMemo(() => {
    if (opportunities.length === 0) return null;

    let maxApplications = 0;
    let mostPopularOpp = null;

    opportunities.forEach((opp) => {
      const appCount = opp.applications_count || 0;
      if (appCount > maxApplications) {
        maxApplications = appCount;
        mostPopularOpp = opp;
      }
    });

    if (!mostPopularOpp) return null;

    // Get application breakdown
    const apps = applicationsData[mostPopularOpp.id] || [];
    const breakdown = {
      total: apps.length,
      pending: apps.filter((a) => a.statut === 'PENDING').length,
      reviewed: apps.filter((a) => a.statut === 'REVIEWED').length,
      accepted: apps.filter((a) => a.statut === 'ACCEPTED').length,
      rejected: apps.filter((a) => a.statut === 'REJECTED').length,
    };

    return { opportunity: mostPopularOpp, breakdown };
  }, [opportunities, applicationsData]);

  if (!mostPopular) {
    return null;
  }

  const { opportunity, breakdown } = mostPopular;
  const title = opportunity.titre || opportunity.title || 'Untitled';
  const type = opportunity.type_opportunite || opportunity.type || '-';
  const status = opportunity.statut || opportunity.status || '-';

  const typeLabel = {
    EMPLOI: 'Job',
    STAGE: 'Internship',
    SAISONNIER: 'Seasonal',
    PROJET: 'Project',
  }[type] || type;

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5 lg:p-6">

      <div className="mb-5">
        <h3 className="text-base font-semibold text-neutral-900 line-clamp-2">
          {title}
        </h3>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="inline-flex rounded-md bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
            {typeLabel}
          </span>
          <span className="inline-flex rounded-md bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
            {status}
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">Total Applications</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">
            {breakdown.total}
          </p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">Pending</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">{breakdown.pending}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">Reviewed</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">{breakdown.reviewed}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">Accepted</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">{breakdown.accepted}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">Rejected</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">{breakdown.rejected}</p>
        </div>
      </div>
    </div>
  );
};

export default MostPopularOpportunity;
