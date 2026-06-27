import { ArrowLeft, ExternalLink, Pencil } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '../../../components/ui/button.jsx';
import { useLanguage } from '../../../i18n/LanguageContext.jsx';
import { organizationOpportunityEditPath } from '../hooks/useOrganizationOpportunityEdit.js';
import {
  ORGANIZATION_OPPORTUNITY_EDITABLE_STATUSES,
  OrganizationOpportunityStatusSelect,
} from './OrganizationOpportunityStatus.jsx';
import { ORGANIZATION_OPPORTUNITY_TYPE_LABELS } from '../utils/organizationOpportunityFormatters.js';
import { getOrganizationOpportunityTypeLabel } from '../utils/organizationLabelUtils.js';

const OrganizationOpportunityDetailHeader = ({
  opportunity,
  organizationName,
  statusActionId,
  onStatusAction,
}) => {
  const { t } = useLanguage();
  const editPath = ORGANIZATION_OPPORTUNITY_EDITABLE_STATUSES.has(opportunity.status)
    ? organizationOpportunityEditPath(opportunity)
    : null;

  return (
    <header className="border-b border-neutral-200 bg-white px-5 py-6 sm:px-8">
      <Link
        to="/organization/dashboard"
        className="inline-flex items-center gap-2 text-sm font-semibold text-blue-700 hover:text-blue-800"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        {t('organization.backToOpportunities')}
      </Link>

      <div className="mt-6 flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium text-neutral-500">
            {getOrganizationOpportunityTypeLabel(
              opportunity.type,
              t,
              ORGANIZATION_OPPORTUNITY_TYPE_LABELS[opportunity.type] || opportunity.type,
            )}
          </p>
          <h1 className="mt-1 break-words text-2xl font-semibold leading-tight text-neutral-950 sm:text-3xl">
            {opportunity.title}
          </h1>
          <p className="mt-2 text-sm text-neutral-600">
            {opportunity.location || t('organization.locationNotSet')}
            {organizationName ? ` · ${organizationName}` : ''}
          </p>
        </div>

        <OrganizationOpportunityStatusSelect
          opportunity={opportunity}
          disabled={statusActionId === opportunity.id}
          onAction={onStatusAction}
        />
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        {editPath ? (
          <Button asChild className="bg-blue-700 text-white hover:bg-blue-800">
            <Link to={editPath}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              {t('organization.editOpportunity')}
            </Link>
          </Button>
        ) : null}
        {opportunity.status === 'ACTIVE' ? (
          <Button asChild variant="outline">
            <Link to={`/opportunities/${opportunity.id}`}>
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              {t('organization.viewPublicPage')}
            </Link>
          </Button>
        ) : null}
      </div>
    </header>
  );
};

export default OrganizationOpportunityDetailHeader;
