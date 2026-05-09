import { Link } from 'react-router-dom';
import {
  Bookmark,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  MapPin,
} from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import OpportunityCompanyAvatar from '../OpportunityCompanyAvatar.jsx';
import { buildOpportunityBrowseCardViewModel } from '../../viewModels/opportunityList.vm.js';

const OpportunityBrowseCard = ({ opportunity, isUserAuthenticated }) => {
  const viewModel = buildOpportunityBrowseCardViewModel(opportunity, isUserAuthenticated);
  const hasRoleDetails = Boolean(
    viewModel.salaryLabel ||
      viewModel.contractTypeLabel ||
      viewModel.workModeLabel ||
      viewModel.experienceLabel ||
      viewModel.languagePreview.length > 0
  );
  const hasSkillPreview = viewModel.skillsPreview.length > 0;

  return (
    <article className="rounded-md border border-neutral-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start gap-4">
        <OpportunityCompanyAvatar
          companyLogo={viewModel.companyLogo}
          organizationLabel={viewModel.organizationLabel}
        />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge className="bg-blue-50 text-blue-800" variant="secondary">
                  {viewModel.typeLabel}
                </Badge>
                <Badge variant={viewModel.statusBadgeVariant}>{viewModel.statusLabel}</Badge>
                {viewModel.sourceLabel ? (
                  <Badge className="border-neutral-200 bg-white text-neutral-700" variant="outline">
                    Source: {viewModel.sourceLabel}
                  </Badge>
                ) : null}
              </div>

              <Link
                to={`/opportunities/${opportunity.id}`}
                className="line-clamp-2 text-lg font-semibold leading-tight text-neutral-950 hover:text-blue-700"
              >
                {viewModel.title}
              </Link>
            </div>

            <Button asChild size="sm" className="hidden bg-neutral-950 text-white hover:bg-neutral-800 sm:inline-flex">
              <Link to={`/opportunities/${opportunity.id}`}>View details</Link>
            </Button>
          </div>

          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm font-medium text-neutral-700">
            {viewModel.organizationLabel ? (
              <span className="inline-flex items-center gap-1.5">
                <Building2 className="h-4 w-4 text-neutral-500" />
                {viewModel.organizationLabel}
              </span>
            ) : null}
            {viewModel.locationLabel ? (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-4 w-4 text-neutral-500" />
                {viewModel.locationLabel}
              </span>
            ) : null}
            {viewModel.deadlineDateLabel ? (
              <span className="inline-flex items-center gap-1.5">
                <CalendarDays className="h-4 w-4 text-neutral-500" />
                Deadline {viewModel.deadlineDateLabel}
              </span>
            ) : null}
            {viewModel.workModeLabel ? (
              <span className="inline-flex items-center gap-1.5">
                <BriefcaseBusiness className="h-4 w-4 text-neutral-500" />
                {viewModel.workModeLabel}
              </span>
            ) : null}
          </div>

          {hasRoleDetails ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {viewModel.salaryLabel ? <Badge variant="outline">{viewModel.salaryLabel}</Badge> : null}
              {viewModel.contractTypeLabel ? (
                <Badge variant="outline">{viewModel.contractTypeLabel}</Badge>
              ) : null}
              {viewModel.experienceLabel ? (
                <Badge variant="outline">{viewModel.experienceLabel}</Badge>
              ) : null}
              {viewModel.languagePreview.length > 0 ? (
                <Badge variant="outline">{viewModel.languagePreview.join(', ')}</Badge>
              ) : null}
            </div>
          ) : null}

          <p className="mt-3 text-sm leading-6 text-neutral-700">{viewModel.descriptionPreview}</p>

          {hasSkillPreview ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {viewModel.skillsPreview.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs font-semibold text-neutral-800"
                >
                  {skill}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 pt-4">
        <p className="text-sm font-medium text-neutral-600">
          {viewModel.publishedAgoLabel
            ? `Published ${viewModel.publishedAgoLabel}`
            : `Published ${viewModel.publishedDateLabel}`}
        </p>

        <div className="flex flex-wrap items-center gap-2">
          {!isUserAuthenticated ? (
            <Button asChild size="sm" variant="outline">
              <Link to="/login">
                <Bookmark className="h-4 w-4" />
                Sign in to save
              </Link>
            </Button>
          ) : null}
          <Button asChild size="sm" className="bg-neutral-950 text-white hover:bg-neutral-800 sm:hidden">
            <Link to={`/opportunities/${opportunity.id}`}>View details</Link>
          </Button>
        </div>
      </div>
    </article>
  );
};

export default OpportunityBrowseCard;
