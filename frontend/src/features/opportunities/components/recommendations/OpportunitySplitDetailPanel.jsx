import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { DETAIL_SIMILAR_OPPORTUNITIES_LIMIT } from '../../constants/opportunityDetail.js';
import { getSimilarOpportunities } from '../../services/opportunitiesService.js';
import OpportunityDescriptionSection from '../detail/OpportunityDescriptionSection.jsx';
import OpportunityExtraData from '../detail/OpportunityExtraData.jsx';
import OpportunityMeta from '../detail/OpportunityMeta.jsx';
import OpportunitySimilarSection from '../detail/OpportunitySimilarSection.jsx';
import OpportunitySkillsSection from '../detail/OpportunitySkillsSection.jsx';
import RecommendationInsightPanel from './RecommendationInsightPanel.jsx';
import { buildOpportunityDetailPageViewModel } from '../../viewModels/opportunityDetail.vm.js';

const VISIBLE_ADDITIONAL_INFO_LABELS = new Set(['Sector', 'Company size', 'Reference']);

const OpportunitySplitDetailPanel = ({ opportunity, isUserAuthenticated }) => {
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [showAllSkills, setShowAllSkills] = useState(false);
  const [similarOpportunities, setSimilarOpportunities] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState(null);
  const scrollContainerRef = useRef(null);

  useEffect(() => {
    setIsDescriptionExpanded(false);
    setShowAllSkills(false);
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({ top: 0, behavior: 'auto' });
    }
  }, [opportunity?.id]);

  useEffect(() => {
    let isCancelled = false;

    if (!isUserAuthenticated || !opportunity?.id) {
      setSimilarOpportunities([]);
      setSimilarLoading(false);
      setSimilarError(null);
      return undefined;
    }

    const fetchSimilar = async () => {
      try {
        setSimilarLoading(true);
        setSimilarError(null);

        const data = await getSimilarOpportunities(opportunity.id, DETAIL_SIMILAR_OPPORTUNITIES_LIMIT);
        if (isCancelled) return;

        setSimilarOpportunities(Array.isArray(data) ? data : []);
      } catch (error) {
        if (isCancelled) return;

        console.log('Failed to load similar opportunities', error);
        setSimilarError(error);
        setSimilarOpportunities([]);
      } finally {
        if (!isCancelled) {
          setSimilarLoading(false);
        }
      }
    };

    fetchSimilar();

    return () => {
      isCancelled = true;
    };
  }, [isUserAuthenticated, opportunity?.id]);

  const viewModel = useMemo(
    () =>
      buildOpportunityDetailPageViewModel({
        opportunity,
        isUserAuthenticated,
        similarOpportunities,
        showAllSkills,
      }),
    [isUserAuthenticated, opportunity, showAllSkills, similarOpportunities],
  );

  if (!viewModel) {
    return (
      <aside className="hidden min-w-0 rounded-md border border-neutral-200 bg-white p-6 text-sm text-neutral-600 lg:block">
        Select a recommendation to review the details.
      </aside>
    );
  }

  const visibleAdditionalInfoItems = viewModel.additionalInfoItems.filter((item) =>
    VISIBLE_ADDITIONAL_INFO_LABELS.has(item.label),
  );

  const handleApply = () => {
    if (!viewModel.sourceUrl) return;
    window.open(viewModel.sourceUrl, '_blank', 'noopener,noreferrer');
  };

  return (
    <aside className="hidden min-w-0 overflow-hidden rounded-md border border-neutral-200 bg-white shadow-sm lg:block">
      <div ref={scrollContainerRef} className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto">
        <div className="border-b border-neutral-200 p-6 xl:p-7">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium text-neutral-600">{viewModel.organizationLabel}</p>
              <h2 className="mt-1 break-words text-2xl font-semibold leading-tight text-neutral-950 xl:text-3xl">
                {viewModel.title}
              </h2>
              <p className="mt-2 text-sm text-neutral-600">{viewModel.displayLocationLabel}</p>
            </div>
            {viewModel.sourceUrl ? (
              <Button type="button" onClick={handleApply} className="shrink-0">
                {viewModel.primaryActionLabel}
                <ExternalLink className="h-4 w-4" />
              </Button>
            ) : null}
          </div>
        </div>

        <div className="space-y-5 p-6 xl:p-7">
          <OpportunityMeta
            isProject={viewModel.isProject}
            organizationLabel={viewModel.organizationLabel}
            projectRegionLabel={viewModel.projectRegionLabel}
            projectProcedureLabel={viewModel.projectProcedureLabel}
            projectFinancementLabel={viewModel.projectFinancementLabel}
            salaryLabel={viewModel.salaryLabel}
            locationLabel={viewModel.locationLabel}
            contractLabel={viewModel.contractLabel}
            availabilityLabel={viewModel.availabilityLabel}
            experienceLabel={viewModel.experienceLabel}
            educationLabel={viewModel.educationLabel}
          />

          {viewModel.recommendation ? (
            <RecommendationInsightPanel recommendation={viewModel.recommendation} context="detail" />
          ) : null}

          <OpportunityDescriptionSection
            descriptionMarkup={viewModel.descriptionMarkup}
            isLongDescription={viewModel.isLongDescription}
            isDescriptionExpanded={isDescriptionExpanded}
            onToggleDescription={() => setIsDescriptionExpanded((previous) => !previous)}
          />

          <OpportunityExtraData
            isProject={viewModel.isProject}
            additionalInfoItems={visibleAdditionalInfoItems}
            organizationLabel={viewModel.organizationLabel}
            publishedDateLabel={viewModel.publishedDateLabel}
            deadlineDateLabel={viewModel.deadlineDateLabel}
            projectRegionLabel={viewModel.projectRegionLabel}
            projectProcedureLabel={viewModel.projectProcedureLabel}
            projectFinancementLabel={viewModel.projectFinancementLabel}
            projectTypeCommandeLabel={viewModel.projectTypeCommandeLabel}
            projectDelaiValiditeLabel={viewModel.projectDelaiValiditeLabel}
            projectCautionLabel={viewModel.projectCautionLabel}
            projectLots={viewModel.projectLots}
          />

          {!viewModel.isProject ? (
            <OpportunitySkillsSection
              skills={viewModel.skills}
              visibleSkills={viewModel.visibleSkills}
              hiddenSkillsCount={viewModel.hiddenSkillsCount}
              showAllSkills={showAllSkills}
              skillsDetectedByAi={viewModel.skillsDetectedByAi}
              onToggleSkills={() => setShowAllSkills((previous) => !previous)}
            />
          ) : null}

          <OpportunitySimilarSection
            isUserAuthenticated={isUserAuthenticated}
            similarOpportunities={viewModel.dedupedSimilar}
            loading={similarLoading}
            error={similarError}
          />
        </div>
      </div>
    </aside>
  );
};

export default OpportunitySplitDetailPanel;
