import { useMemo } from 'react';

import { useLanguage } from '../../../i18n/LanguageContext.jsx';
import {
  getOrganizationOpportunityStatusLabel,
  getOrganizationOpportunityTypeLabel,
} from '../utils/organizationLabelUtils.js';

const MostPopularOpportunity = ({ opportunities, applicationsData }) => {
  const { t } = useLanguage();
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
  const title = opportunity.titre || opportunity.title || t('organization.untitledOpportunity');
  const type = opportunity.type_opportunite || opportunity.type || '-';
  const status = opportunity.statut || opportunity.status || '-';

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5 lg:p-6">

      <div className="mb-5">
        <h3 className="text-base font-semibold text-neutral-900 line-clamp-2">
          {title}
        </h3>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="inline-flex rounded-md bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
            {getOrganizationOpportunityTypeLabel(type, t)}
          </span>
          <span className="inline-flex rounded-md bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
            {getOrganizationOpportunityStatusLabel(status, t)}
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">{t('organization.totalApplications')}</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">
            {breakdown.total}
          </p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">{t('organization.pending')}</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">{breakdown.pending}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">{t('organization.reviewed')}</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">{breakdown.reviewed}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">{t('organization.accepted')}</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">{breakdown.accepted}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-3">
          <p className="text-xs text-neutral-500">{t('organization.rejected')}</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">{breakdown.rejected}</p>
        </div>
      </div>
    </div>
  );
};

export default MostPopularOpportunity;
