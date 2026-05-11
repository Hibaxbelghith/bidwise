import {
  ArrowLeft,
  Calendar,
  MapPin,
} from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import OpportunityCompanyAvatar from '../OpportunityCompanyAvatar.jsx';
import RecommendationMatchBadge from '../recommendations/RecommendationMatchBadge.jsx';
import { hasDisplayValue } from '../../utils/opportunityHelpers.js';

const OpportunityHeader = ({
  title,
  typeLabel,
  statusLabel,
  statusBadgeVariant,
  organizationLabel,
  displayLocationLabel,
  publishedDateLabel,
  deadlineDateLabel,
  companyLogo,
  recommendation,
  onBack,
}) => (
  <header className="border-b border-neutral-200 bg-white">
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <button
        type="button"
        className="inline-flex items-center gap-2 text-sm font-medium text-neutral-600 hover:text-neutral-900"
        onClick={onBack}
      >
        <ArrowLeft className="h-4 w-4" />
        Back to opportunities
      </button>

      <div className="mt-5 flex items-start gap-4">
        <OpportunityCompanyAvatar
          companyLogo={companyLogo}
          organizationLabel={organizationLabel}
          containerClassName="relative flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-neutral-200 bg-white shadow-sm"
          iconClassName="h-8 w-8 text-neutral-400"
          imageClassName="absolute inset-0 h-full w-full rounded-2xl bg-white object-contain"
        />

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold leading-tight text-neutral-900 sm:text-3xl">{title}</h1>
            <Badge>{typeLabel}</Badge>
            <Badge variant={statusBadgeVariant}>{statusLabel}</Badge>
            <RecommendationMatchBadge recommendation={recommendation} />
          </div>

          {organizationLabel ? <p className="text-base text-neutral-600 sm:text-lg">{organizationLabel}</p> : null}

          <div className="mt-3 flex flex-wrap gap-3 text-xs font-medium text-neutral-600 sm:text-sm">
            {hasDisplayValue(displayLocationLabel) ? (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-4 w-4" />
                {displayLocationLabel}
              </span>
            ) : null}
            <span className="inline-flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              Published: {publishedDateLabel}
            </span>
            {deadlineDateLabel ? (
              <span className="inline-flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                Deadline: {deadlineDateLabel}
              </span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  </header>
);

export default OpportunityHeader;
