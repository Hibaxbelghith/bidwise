import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

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
import OpportunityAssistantCard from '../components/recommendations/OpportunityAssistantCard.jsx';
import OpportunityApplicationDialog from '../components/application/OpportunityApplicationDialog.jsx';
import ExternalApplicationFollowUpDialog from '../components/application/ExternalApplicationFollowUpDialog.jsx';
import { useOpportunityDetailPage } from '../hooks/useOpportunityDetailPage.js';

const VISIBLE_ADDITIONAL_INFO_LABELS = new Set(['Sector', 'Company size', 'Reference']);

const OpportunityDetailPage = () => {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading, user, refreshUser } = useAuth();
  const [applicationOpen, setApplicationOpen] = useState(false);
  const continueApplicationHandledRef = useRef(false);
  const isUserAuthenticated = !authLoading && isAuthenticated;
  const shouldContinueExternalApplication = new URLSearchParams(location.search).get('continueApplication') === '1';
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
    initialRecommendation: location.state?.recommendation || null,
  });
  const viewModel = detailPage.viewModel;
  const isCandidate = user?.account_type === 'candidate';
  const isDirectApplication = Boolean(viewModel?.acceptsDirectApplications && isCandidate);

  useLayoutEffect(() => {
    if (typeof window === 'undefined') return;
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, [id]);

  useEffect(() => {
    if (
      continueApplicationHandledRef.current
      || !shouldContinueExternalApplication
      || detailPage.loading
      || !viewModel
      || !isCandidate
      || !detailPage.canApply
      || isDirectApplication
      || detailPage.isApplied
    ) {
      return;
    }

    continueApplicationHandledRef.current = true;
    void detailPage.handleApply();
  }, [
    detailPage,
    isCandidate,
    isDirectApplication,
    shouldContinueExternalApplication,
    viewModel,
  ]);

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

  const visibleAdditionalInfoItems = viewModel.additionalInfoItems.filter((item) => (
    VISIBLE_ADDITIONAL_INFO_LABELS.has(item.label)
  ));
  const handlePrimaryAction = async () => {
    if (isDirectApplication) {
      setApplicationOpen(true);
      return;
    }
    await detailPage.handleApply();
  };
  const handleApplicationSubmitted = () => {
    detailPage.markApplied();
    setApplicationOpen(false);
    toast.success('Application submitted successfully.');
  };

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

          <aside className="hidden space-y-4 lg:sticky lg:top-24 lg:block lg:self-start">
            <OpportunityActionPanel
              snapshotProps={viewModel.snapshotProps}
              isUserAuthenticated={isUserAuthenticated}
              isSaved={detailPage.isSaved}
              canApply={detailPage.canApply && isCandidate}
              primaryActionLabel={viewModel.primaryActionLabel}
              onApply={handlePrimaryAction}
              onSave={detailPage.handleSave}
              isApplied={detailPage.isApplied}
              isDirectApplication={isDirectApplication}
              isApplyingExternally={detailPage.isApplyingExternally}
            />
          </aside>
        </div>
      </main>

      <OpportunityAssistantCard
        opportunityId={id}
        locked={!isUserAuthenticated}
        floating
      />

      <OpportunityActionBar
        isUserAuthenticated={isUserAuthenticated}
        isSaved={detailPage.isSaved}
        canApply={detailPage.canApply && isCandidate}
        primaryActionLabel={viewModel.primaryActionLabel}
        onApply={handlePrimaryAction}
        onSave={detailPage.handleSave}
        isApplied={detailPage.isApplied}
        isDirectApplication={isDirectApplication}
        isApplyingExternally={detailPage.isApplyingExternally}
      />

      {isDirectApplication ? (
        <OpportunityApplicationDialog
          open={applicationOpen}
          onOpenChange={setApplicationOpen}
          opportunity={viewModel}
          organizationLabel={viewModel.organizationLabel}
          user={user}
          onUserRefresh={refreshUser}
          onSubmitted={handleApplicationSubmitted}
        />
      ) : null}

      <ExternalApplicationFollowUpDialog
        open={detailPage.externalPromptOpen}
        onOpenChange={detailPage.closeExternalPrompt}
        opportunityTitle={detailPage.pendingExternalApplication?.title || viewModel.title}
        organizationLabel={detailPage.pendingExternalApplication?.organizationLabel || viewModel.organizationLabel}
        sourceUrl={detailPage.pendingExternalApplication?.sourceUrl || viewModel.sourceUrl}
        isBusy={detailPage.externalPromptBusy}
        error={detailPage.externalPromptError}
        onConfirmApplied={detailPage.handleExternalApplicationConfirmed}
        onNotYet={detailPage.handleExternalApplicationNotYet}
        onRemindLater={detailPage.handleExternalApplicationRemindLater}
      />
    </div>
  );
};

export default OpportunityDetailPage;
