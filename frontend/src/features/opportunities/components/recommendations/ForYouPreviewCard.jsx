import { memo } from 'react';
import { BriefcaseBusiness, Globe2, MapPin, Sparkles } from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import OpportunityCompanyAvatar from '../OpportunityCompanyAvatar.jsx';
import RecommendationMatchBadge from './RecommendationMatchBadge.jsx';
import { buildRecommendationViewModel } from '../../utils/recommendationUtils.js';
import { buildOpportunityBrowseCardViewModel } from '../../viewModels/opportunityList.vm.js';

const ForYouPreviewCard = memo(({
  opportunity,
  isSelected = false,
  isUserAuthenticated,
  onSelect,
}) => {
  const viewModel = buildOpportunityBrowseCardViewModel(opportunity, isUserAuthenticated);
  const recommendation = opportunity?.recommendation || opportunity;
  const recommendationVm = buildRecommendationViewModel(recommendation, { compact: true });
  const reasons = recommendationVm?.visibleReasons?.slice(0, 2) || [];
  const signalChips = recommendationVm?.signalChips?.slice(0, 3) || [];
  const skills = viewModel.skillsPreview.slice(0, 2);

  return (
    <button
      type="button"
      id={opportunity?.id ? `opportunity-card-${opportunity.id}` : undefined}
      onClick={onSelect}
      className={[
        'group w-full rounded-md border bg-white p-3 text-left shadow-sm transition',
        'hover:border-blue-300 hover:bg-blue-50/20 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
        isSelected ? 'border-blue-500 bg-blue-50/40 ring-2 ring-blue-500 ring-offset-2' : 'border-neutral-200',
      ].join(' ')}
      aria-pressed={isSelected}
    >
      <div className="flex min-w-0 gap-3">
        <OpportunityCompanyAvatar
          companyLogo={viewModel.companyLogo}
          organizationLabel={viewModel.organizationLabel}
          containerClassName="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-neutral-200 bg-white"
          imageClassName="absolute inset-0 h-full w-full rounded-md bg-white object-contain"
          iconClassName="h-4 w-4 text-neutral-400"
        />
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-neutral-950 group-hover:text-blue-950">
                {viewModel.title}
              </h3>
              {viewModel.organizationLabel ? (
                <p className="mt-1 truncate text-xs font-medium text-neutral-600">
                  {viewModel.organizationLabel}
                </p>
              ) : null}
            </div>
            <RecommendationMatchBadge recommendation={recommendation} className="shrink-0 text-xs" />
          </div>

          {viewModel.sourceLabel ? (
            <div className="mt-2">
              <Badge
                variant="outline"
                className="max-w-full rounded-md border-cyan-200 bg-cyan-50 px-2 py-0.5 text-[11px] font-semibold text-cyan-800"
              >
                <Globe2 className="mr-1 h-3 w-3 shrink-0" aria-hidden="true" />
                <span className="truncate">{viewModel.sourceLabel}</span>
              </Badge>
            </div>
          ) : null}

          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-neutral-600">
            {viewModel.locationLabel ? (
              <span className="inline-flex min-w-0 items-center gap-1">
                <MapPin className="h-3.5 w-3.5 shrink-0 text-neutral-500" aria-hidden="true" />
                <span className="truncate">{viewModel.locationLabel}</span>
              </span>
            ) : null}
            {viewModel.contractTypeLabel ? (
              <span className="inline-flex min-w-0 items-center gap-1">
                <BriefcaseBusiness className="h-3.5 w-3.5 shrink-0 text-neutral-500" aria-hidden="true" />
                <span className="truncate">{viewModel.contractTypeLabel}</span>
              </span>
            ) : null}
            {viewModel.experienceLabel ? (
              <span className="truncate">{viewModel.experienceLabel}</span>
            ) : null}
          </div>

          {reasons.length > 0 ? (
            <ul className="mt-3 space-y-1 text-xs text-neutral-700">
              {reasons.map((reason) => (
                <li key={reason} className="flex min-w-0 items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 shrink-0 text-blue-600" aria-hidden="true" />
                  <span className="truncate">{reason}</span>
                </li>
              ))}
            </ul>
          ) : null}

          {signalChips.length > 0 || skills.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {signalChips.map((chip) => (
                <Badge
                  key={chip.key}
                  variant="secondary"
                  className="max-w-full truncate rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-800"
                >
                  {chip.label}
                </Badge>
              ))}
              {skills.map((skill) => (
                <Badge key={skill} variant="outline" className="max-w-full truncate rounded-md px-2 py-0.5 text-xs">
                  {skill}
                </Badge>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </button>
  );
});

ForYouPreviewCard.displayName = 'ForYouPreviewCard';

export default ForYouPreviewCard;
