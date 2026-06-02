import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

import { useAuth } from '../../auth/AuthContext.jsx';
import OpportunityActionBar from '../components/detail/OpportunityActionBar.jsx';
import OpportunityActionPanel from '../components/detail/OpportunityActionPanel.jsx';
import OpportunityDescriptionSection from '../components/detail/OpportunityDescriptionSection.jsx';
import OpportunityDetailSkeleton from '../components/detail/OpportunityDetailSkeleton.jsx';
import OpportunityDocuments from '../components/detail/OpportunityDocuments.jsx';
import OpportunityExtraData from '../components/detail/OpportunityExtraData.jsx';
import OpportunityHeader from '../components/detail/OpportunityHeader.jsx';
import OpportunityMeta from '../components/detail/OpportunityMeta.jsx';
import OpportunitySimilarSection from '../components/detail/OpportunitySimilarSection.jsx';
import OpportunitySkillsSection from '../components/detail/OpportunitySkillsSection.jsx';
import RecommendationInsightPanel, {
  RecommendationInsightSkeleton,
} from '../components/recommendations/RecommendationInsightPanel.jsx';
import ResumeFitCtaCard from '../components/recommendations/ResumeFitCtaCard.jsx';
import { useOpportunityDetailPage } from '../hooks/useOpportunityDetailPage.js';
import { hasActiveResume } from '../utils/recommendationUtils.js';

const VISIBLE_ADDITIONAL_INFO_LABELS = new Set(['Sector', 'Company size', 'Reference']);

const OpportunityDetailPage = () => {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading, user } = useAuth();
  const isUserAuthenticated = !authLoading && isAuthenticated;
  const userHasResume = hasActiveResume(user);
  const handleBackToOpportunities = () => {
    if (location.state?.returnTab) {
      navigate('/opportunities', {
        state: {
          returnTab: location.state.returnTab,
          scrollY: location.state.scrollY,
          opportunityId: location.state.opportunityId,
        },
      });
      return;
    }

    navigate('/opportunities');
  };
  const detailPage = useOpportunityDetailPage({
    opportunityId: id,
    isUserAuthenticated,
  });

  if (detailPage.loading) {
    return <OpportunityDetailSkeleton />;
  }

  if (detailPage.error || !detailPage.viewModel) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
        <button
          type="button"
          className="inline-flex items-center gap-2 text-neutral-600"
          onClick={handleBackToOpportunities}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to opportunities
        </button>
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
          {detailPage.error || 'Opportunity not found'}
        </div>
      </div>
    );
  }

  const { viewModel } = detailPage;
  const visibleAdditionalInfoItems = viewModel.additionalInfoItems.filter((item) => (
    VISIBLE_ADDITIONAL_INFO_LABELS.has(item.label)
  ));

  return (
    <div className="min-h-screen bg-neutral-50 pb-32">
      <OpportunityHeader
        title={viewModel.title}
        typeLabel={viewModel.typeLabel}
        statusLabel={viewModel.statusLabel}
        statusBadgeVariant={viewModel.statusBadgeVariant}
        organizationLabel={viewModel.organizationLabel}
        displayLocationLabel={viewModel.displayLocationLabel}
        publishedDateLabel={viewModel.publishedDateLabel}
        deadlineDateLabel={viewModel.deadlineDateLabel}
        companyLogo={viewModel.companyLogo}
        recommendation={viewModel.recommendation}
        onBack={handleBackToOpportunities}
      />

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
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

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-6">
            {viewModel.recommendation ? (
              <RecommendationInsightPanel recommendation={viewModel.recommendation} context="detail" />
            ) : detailPage.recommendationLoading && isUserAuthenticated ? (
              <RecommendationInsightSkeleton />
            ) : !detailPage.recommendationLoading && isUserAuthenticated && !userHasResume ? (
              <ResumeFitCtaCard />
            ) : null}

            <OpportunityDescriptionSection
              descriptionMarkup={viewModel.descriptionMarkup}
              isLongDescription={viewModel.isLongDescription}
              isDescriptionExpanded={detailPage.isDescriptionExpanded}
              onToggleDescription={detailPage.toggleDescription}
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

            {!viewModel.isProject && viewModel.projectDocuments.length ? (
              <OpportunityDocuments documents={viewModel.projectDocuments} />
            ) : null}

            {viewModel.isProject && viewModel.hasProjectDocuments ? (
              <div className="mt-5">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-base font-semibold text-neutral-900">Documents</h3>
                  <p className="text-xs text-neutral-500">
                    Open the official source files attached to this tender.
                  </p>
                </div>
                <OpportunityDocuments documents={viewModel.projectDocuments} />
              </div>
            ) : null}

            {!viewModel.isProject ? (
              <OpportunitySkillsSection
                skills={viewModel.skills}
                visibleSkills={viewModel.visibleSkills}
                hiddenSkillsCount={viewModel.hiddenSkillsCount}
                showAllSkills={detailPage.showAllSkills}
                skillsDetectedByAi={viewModel.skillsDetectedByAi}
                onToggleSkills={detailPage.toggleSkills}
              />
            ) : null}


            <OpportunitySimilarSection
              isUserAuthenticated={isUserAuthenticated}
              similarOpportunities={viewModel.dedupedSimilar}
              loading={detailPage.similarLoading}
              error={detailPage.similarError}
            />
          </div>

          <aside className="hidden lg:sticky lg:top-24 lg:block lg:self-start">
            <OpportunityActionPanel
              snapshotProps={viewModel.snapshotProps}
              isUserAuthenticated={isUserAuthenticated}
              isSaved={detailPage.isSaved}
              canApply={detailPage.canApply}
              primaryActionLabel={viewModel.primaryActionLabel}
              onApply={detailPage.handleApply}
              onSave={detailPage.handleSave}
            />
          </aside>
        </div>
      </main>

      <OpportunityActionBar
        isUserAuthenticated={isUserAuthenticated}
        isSaved={detailPage.isSaved}
        canApply={detailPage.canApply}
        primaryActionLabel={viewModel.primaryActionLabel}
        onApply={detailPage.handleApply}
        onSave={detailPage.handleSave}
      />
    </div>
  );
};

export default OpportunityDetailPage;
