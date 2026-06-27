import { memo, useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Bookmark,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  ClipboardList,
  FileText,
  Layers3,
  MapPin,
} from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import OpportunityCompanyAvatar from '../OpportunityCompanyAvatar.jsx';
import RecommendationInsightPanel from '../recommendations/RecommendationInsightPanel.jsx';
import RecommendationMatchBadge from '../recommendations/RecommendationMatchBadge.jsx';
import {
  isOpportunitySaved,
  listenSavedOpportunityChanges,
  toggleSavedOpportunity,
} from '../../utils/savedOpportunityStorage.js';
import { buildOpportunityBrowseCardViewModel } from '../../viewModels/opportunityList.vm.js';

const getRecommendationPayload = (opportunity) => {
  if (opportunity?.recommendation) return opportunity.recommendation;

  const payload = opportunity;
  if (!payload) return null;

  const hasRecommendationSignal = Boolean(
    payload.score_label ||
      payload.recommendation_confidence ||
      payload.recommendation_mode ||
      payload.recommendation_bucket ||
      payload.recommendation_bucket_reason ||
      payload.tender_recommendation,
  );

  return hasRecommendationSignal ? payload : null;
};

const getTenderPriorityClassName = (priority) => {
  const normalized = String(priority || '').toLowerCase();
  if (normalized.includes('forte') || normalized.includes('strong')) {
    return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  }
  if (normalized.includes('surveiller') || normalized.includes('watch')) {
    return 'border-amber-200 bg-amber-50 text-amber-800';
  }
  if (normalized.includes('veille') || normalized.includes('general')) {
    return 'border-blue-200 bg-blue-50 text-blue-800';
  }
  if (normalized.includes('faible') || normalized.includes('low')) {
    return 'border-neutral-200 bg-neutral-50 text-neutral-700';
  }
  return 'border-neutral-200 bg-neutral-50 text-neutral-700';
};

const OpportunityBrowseCard = memo(({
  opportunity,
  isUserAuthenticated,
  showRecommendationInsights = false,
  returnTab = 'explore',
}) => {
  const location = useLocation();
  const { t } = useLanguage();
  const viewModel = useMemo(
    () => buildOpportunityBrowseCardViewModel(opportunity, isUserAuthenticated),
    [isUserAuthenticated, opportunity],
  );
  const recommendation = useMemo(() => getRecommendationPayload(opportunity), [opportunity]);
  const tenderRecommendation = viewModel.isProject ? viewModel.tenderRecommendation : null;
  const [isSaved, setIsSaved] = useState(() => isOpportunitySaved(opportunity?.id));
  const hasRoleDetails = Boolean(
    !viewModel.isProject && (
      viewModel.salaryLabel ||
      viewModel.contractTypeLabel ||
      viewModel.workModeLabel ||
      viewModel.experienceLabel ||
      viewModel.languagePreview.length > 0
    )
  );
  const hasSkillPreview = !viewModel.isProject && viewModel.skillsPreview.length > 0;
  const tenderReasons = Array.isArray(tenderRecommendation?.reasons)
    ? tenderRecommendation.reasons.slice(0, 3)
    : [];
  const detailState = {
    from: location,
    returnTab,
    scrollY: typeof window !== 'undefined' ? window.scrollY : 0,
    opportunityId: opportunity?.id ?? null,
    recommendation,
  };

  useEffect(() => {
    if (!isUserAuthenticated || !opportunity?.id) {
      setIsSaved(false);
      return undefined;
    }

    setIsSaved(isOpportunitySaved(opportunity.id));
    return listenSavedOpportunityChanges(() => {
      setIsSaved(isOpportunitySaved(opportunity.id));
    });
  }, [isUserAuthenticated, opportunity?.id]);

  const handleToggleSave = () => {
    if (!isUserAuthenticated || !opportunity?.id) return;

    setIsSaved(toggleSavedOpportunity(opportunity.id));
  };

  return (
    <article
      id={opportunity?.id ? `opportunity-card-${opportunity.id}` : undefined}
      className={[
        'rounded-md border bg-white p-5 shadow-sm transition-shadow hover:shadow-md',
        recommendation ? 'border-blue-200' : 'border-neutral-200',
      ].join(' ')}
    >
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
                    {t('opportunities.card.source')}: {viewModel.sourceLabel}
                  </Badge>
                ) : null}
                {!viewModel.isProject ? (
                  <RecommendationMatchBadge
                    recommendation={recommendation}
                    className="sm:hidden"
                  />
                ) : null}
                {viewModel.isProject && tenderRecommendation?.priority ? (
                  <Badge
                    variant="outline"
                    className={getTenderPriorityClassName(tenderRecommendation.priority)}
                  >
                    {tenderRecommendation.priority}
                  </Badge>
                ) : null}
              </div>

              <Link
                to={`/opportunities/${opportunity.id}`}
                state={detailState}
                className="line-clamp-2 text-lg font-semibold leading-tight text-neutral-950 hover:text-blue-700"
              >
                {viewModel.title}
              </Link>
            </div>

            <div className="hidden shrink-0 flex-col items-end gap-2 sm:flex">
              {!viewModel.isProject ? (
                <RecommendationMatchBadge recommendation={recommendation} />
              ) : tenderRecommendation?.priority ? (
                <Badge
                  variant="outline"
                  className={getTenderPriorityClassName(tenderRecommendation.priority)}
                >
                  {tenderRecommendation.priority}
                </Badge>
              ) : null}
              <Button asChild size="sm" className="bg-neutral-950 text-white hover:bg-neutral-800">
                <Link to={`/opportunities/${opportunity.id}`} state={detailState}>
                  {t('opportunities.card.viewDetails')}
                </Link>
              </Button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm font-medium text-neutral-700">
            {viewModel.organizationLabel ? (
              <span className="inline-flex items-center gap-1.5">
                <Building2 className="h-4 w-4 text-neutral-500" />
                {viewModel.organizationLabel}
              </span>
            ) : null}
            {(viewModel.isProject ? viewModel.projectRegionLabel : viewModel.locationLabel) ? (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-4 w-4 text-neutral-500" />
                {viewModel.isProject ? viewModel.projectRegionLabel : viewModel.locationLabel}
              </span>
            ) : null}
            {viewModel.deadlineDateLabel ? (
              <span className="inline-flex items-center gap-1.5">
                <CalendarDays className="h-4 w-4 text-neutral-500" />
                {t('opportunities.card.deadline')} {viewModel.deadlineDateLabel}
              </span>
            ) : null}
            {!viewModel.isProject && viewModel.workModeLabel ? (
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

          {viewModel.isProject ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {viewModel.projectTypeCommandeLabel ? (
                <Badge variant="outline">
                  <ClipboardList className="h-3.5 w-3.5" />
                  {viewModel.projectTypeCommandeLabel}
                </Badge>
              ) : null}
              {viewModel.projectProcedureLabel ? (
                <Badge variant="outline">{viewModel.projectProcedureLabel}</Badge>
              ) : null}
              {viewModel.projectCautionLabel ? (
                <Badge variant="outline">{t('opportunities.card.caution')}: {viewModel.projectCautionLabel}</Badge>
              ) : null}
              {viewModel.projectLotsCount ? (
                <Badge variant="outline">
                  <Layers3 className="h-3.5 w-3.5" />
                  {viewModel.projectLotsCount} {t(viewModel.projectLotsCount > 1 ? 'opportunities.card.lots' : 'opportunities.card.lot')}
                </Badge>
              ) : null}
              {viewModel.projectDocumentsCount ? (
                <Badge variant="outline">
                  <FileText className="h-3.5 w-3.5" />
                  {viewModel.projectDocumentsCount} {t(viewModel.projectDocumentsCount > 1 ? 'opportunities.card.documents' : 'opportunities.card.document')}
                </Badge>
              ) : null}
            </div>
          ) : null}

          <p className="mt-3 text-sm leading-6 text-neutral-700">{viewModel.descriptionPreview}</p>

          {viewModel.isProject && tenderReasons.length > 0 ? (
            <div className="mt-4 rounded-md border border-blue-100 bg-blue-50/70 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-900">
                {t('opportunities.card.whyPriority')}
              </p>
              <ul className="mt-2 space-y-1 text-sm text-blue-900">
                {tenderReasons.map((reason) => (
                  <li key={reason} className="flex gap-2">
                    <span aria-hidden="true">-</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

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

          {showRecommendationInsights && recommendation ? (
            <RecommendationInsightPanel
              recommendation={recommendation}
              compact
              className="mt-4"
            />
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 pt-4">
        <p className="text-sm font-medium text-neutral-600">
          {viewModel.publishedAgoLabel
            ? `${t('opportunities.card.published')} ${viewModel.publishedAgoLabel}`
            : `${t('opportunities.card.published')} ${viewModel.publishedDateLabel}`}
        </p>

        <div className="flex flex-wrap items-center gap-2">
          {isUserAuthenticated ? (
            <Button
              type="button"
              size="sm"
              variant={isSaved ? 'default' : 'outline'}
              aria-pressed={isSaved}
              onClick={handleToggleSave}
              className={isSaved ? 'bg-blue-600 text-white hover:bg-blue-700' : ''}
            >
              <Bookmark className={isSaved ? 'h-4 w-4 fill-current' : 'h-4 w-4'} />
              {isSaved ? t('opportunities.card.saved') : t('opportunities.card.save')}
            </Button>
          ) : (
            <Button asChild size="sm" variant="outline">
              <Link to="/login">
                <Bookmark className="h-4 w-4" />
                {t('opportunities.card.signInToSave')}
              </Link>
            </Button>
          )}
          <Button asChild size="sm" className="bg-neutral-950 text-white hover:bg-neutral-800 sm:hidden">
            <Link to={`/opportunities/${opportunity.id}`} state={detailState}>
              {t('opportunities.card.viewDetails')}
            </Link>
          </Button>
        </div>
      </div>
    </article>
  );
});

OpportunityBrowseCard.displayName = 'OpportunityBrowseCard';

export default OpportunityBrowseCard;
