import { Link } from 'react-router-dom';
import { Building2, CalendarDays, Lock, MapPin } from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import OpportunityCompanyAvatar from '../OpportunityCompanyAvatar.jsx';
import { buildOpportunityBrowseCardViewModel } from '../../viewModels/opportunityList.vm.js';

const OpportunityBrowseCard = ({ opportunity, isUserAuthenticated }) => {
  const viewModel = buildOpportunityBrowseCardViewModel(opportunity, isUserAuthenticated);

  return (
    <article className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="mb-3 flex items-start gap-4">
        <OpportunityCompanyAvatar
          companyLogo={viewModel.companyLogo}
          organizationLabel={viewModel.organizationLabel}
        />

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Link
              to={`/opportunities/${opportunity.id}`}
              className="text-lg font-semibold leading-tight text-neutral-900 hover:text-blue-700"
            >
              {viewModel.title}
            </Link>
            <Badge variant="secondary">{viewModel.typeLabel}</Badge>
            <Badge variant={viewModel.statusBadgeVariant}>{viewModel.statusLabel}</Badge>
            <Badge
              variant="outline"
              className={isUserAuthenticated ? 'border-blue-200 bg-blue-50 text-blue-700' : ''}
            >
              {isUserAuthenticated ? (
                viewModel.aiHint
              ) : (
                <span className="inline-flex items-center gap-1">
                  <Lock className="h-3 w-3" />
                  {viewModel.aiHint}
                </span>
              )}
            </Badge>
          </div>

          <div className="mb-3 flex flex-wrap gap-x-4 gap-y-2 text-sm text-neutral-700">
            {viewModel.organizationLabel ? (
              <span className="inline-flex items-center gap-1">
                <Building2 className="h-4 w-4" />
                {viewModel.organizationLabel}
              </span>
            ) : null}
            {viewModel.locationLabel ? (
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-4 w-4" />
                {viewModel.locationLabel}
              </span>
            ) : null}
            <span className="inline-flex items-center gap-1">
              <CalendarDays className="h-4 w-4" />
              Published: {viewModel.publishedDateLabel}
            </span>
            {viewModel.deadlineDateLabel ? (
              <span className="inline-flex items-center gap-1">
                <CalendarDays className="h-4 w-4" />
                Deadline: {viewModel.deadlineDateLabel}
              </span>
            ) : null}
          </div>

          {(viewModel.salaryLabel ||
            viewModel.experienceLabel ||
            viewModel.languagePreview.length > 0) && (
            <div className="mb-3 flex flex-wrap gap-2">
              {viewModel.salaryLabel ? <Badge variant="outline">Salary: {viewModel.salaryLabel}</Badge> : null}
              {viewModel.experienceLabel ? (
                <Badge variant="outline">Experience: {viewModel.experienceLabel}</Badge>
              ) : null}
              {viewModel.languagePreview.length > 0 ? (
                <Badge variant="outline">Languages: {viewModel.languagePreview.join(', ')}</Badge>
              ) : null}
            </div>
          )}

          <p className="text-sm leading-6 text-neutral-700">{viewModel.descriptionPreview}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 pt-4">
        <p className="text-xs text-neutral-500">
          {isUserAuthenticated
            ? 'Open details for match explanation, similar opportunities, and actions.'
            : 'Login to unlock AI match score and action workflow.'}
        </p>

        <div className="flex items-center gap-2">
          {!isUserAuthenticated ? (
            <Button asChild size="sm" variant="outline">
              <Link to="/login">Login</Link>
            </Button>
          ) : null}
          <Button asChild size="sm">
            <Link to={`/opportunities/${opportunity.id}`}>View details</Link>
          </Button>
        </div>
      </div>
    </article>
  );
};

export default OpportunityBrowseCard;
