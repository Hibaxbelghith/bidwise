import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { DETAIL_SIMILAR_OPPORTUNITIES_LIMIT } from '../../constants/opportunityDetail.js';
import {
  generateResumeMatchAction,
  generateResumeMatchAnalysis,
  getResumeMatch,
  getSimilarOpportunities,
} from '../../services/opportunitiesService.js';
import OpportunityDescriptionSection from '../detail/OpportunityDescriptionSection.jsx';
import OpportunityExtraData from '../detail/OpportunityExtraData.jsx';
import OpportunityMeta from '../detail/OpportunityMeta.jsx';
import OpportunitySimilarSection from '../detail/OpportunitySimilarSection.jsx';
import OpportunitySkillsSection from '../detail/OpportunitySkillsSection.jsx';
import RecommendationInsightPanel from './RecommendationInsightPanel.jsx';
import ResumeMatchPanel from './ResumeMatchPanel.jsx';
import { buildOpportunityDetailPageViewModel } from '../../viewModels/opportunityDetail.vm.js';

const VISIBLE_ADDITIONAL_INFO_LABELS = new Set(['Sector', 'Company size', 'Reference']);
const RESUME_MATCH_MIN_THINKING_MS = 900;

const waitForMinimumDelay = async (startedAt, minimumDelay = RESUME_MATCH_MIN_THINKING_MS) => {
  const elapsed = Date.now() - startedAt;
  const remaining = Math.max(0, minimumDelay - elapsed);
  if (remaining > 0) {
    await new Promise((resolve) => {
      window.setTimeout(resolve, remaining);
    });
  }
};

const OpportunitySplitDetailPanel = ({ opportunity, isUserAuthenticated }) => {
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [showAllSkills, setShowAllSkills] = useState(false);
  const [similarOpportunities, setSimilarOpportunities] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState(null);
  const [showResumeMatch, setShowResumeMatch] = useState(false);
  const [resumeMatch, setResumeMatch] = useState(null);
  const [resumeMatchLoading, setResumeMatchLoading] = useState(false);
  const [resumeMatchError, setResumeMatchError] = useState('');
  const [resumeMatchAiAnalysis, setResumeMatchAiAnalysis] = useState(null);
  const [resumeMatchAiLoading, setResumeMatchAiLoading] = useState(false);
  const [resumeMatchAiError, setResumeMatchAiError] = useState('');
  const [resumeMatchActionResults, setResumeMatchActionResults] = useState([]);
  const [resumeMatchActionLoading, setResumeMatchActionLoading] = useState('');
  const [resumeMatchActionError, setResumeMatchActionError] = useState('');
  const scrollContainerRef = useRef(null);

  useEffect(() => {
    setIsDescriptionExpanded(false);
    setShowAllSkills(false);
    setShowResumeMatch(false);
    setResumeMatch(null);
    setResumeMatchLoading(false);
    setResumeMatchError('');
    setResumeMatchAiAnalysis(null);
    setResumeMatchAiLoading(false);
    setResumeMatchAiError('');
    setResumeMatchActionResults([]);
    setResumeMatchActionLoading('');
    setResumeMatchActionError('');
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

  const handleResumeMatch = async () => {
    setShowResumeMatch(true);

    if (!opportunity?.id || resumeMatchLoading || resumeMatchAiLoading) {
      return;
    }

    try {
      const startedAt = Date.now();
      setResumeMatchError('');
      setResumeMatch(null);
      setResumeMatchAiAnalysis(null);
      setResumeMatchAiError('');
      setResumeMatchActionResults([]);
      setResumeMatchActionLoading('');
      setResumeMatchActionError('');

      const initialMatch = await getResumeMatch(opportunity.id);
      setResumeMatch(initialMatch);

      if (initialMatch?.has_resume === false || initialMatch?.status !== 'READY') {
        return;
      }

      setResumeMatchLoading(true);
      const data = await generateResumeMatchAnalysis(opportunity.id);
      await waitForMinimumDelay(startedAt);
      if (data?.status === 'fallback' || data?.source === 'deterministic') {
        setResumeMatch({
          ...(data?.evidence || {}),
          deterministic_analysis: data?.analysis || null,
          can_generate_ai_analysis: true,
        });
        setResumeMatchAiError(
          data?.error || 'The full AI analysis is not available right now. Showing the quick BidWise analysis instead.',
        );
      } else {
        setResumeMatchAiAnalysis(data);
      }
    } catch (error) {
      console.log('Failed to generate resume match analysis', error);

      try {
        const fallbackStartedAt = Date.now();
        const fallback = await getResumeMatch(opportunity.id);
        await waitForMinimumDelay(fallbackStartedAt, 500);
        setResumeMatch(fallback);
        setResumeMatchAiError(
          error?.response?.data?.detail || 'The full AI analysis is not available right now. Showing the quick BidWise analysis instead.',
        );
      } catch (fallbackError) {
        console.log('Failed to load resume match fallback', fallbackError);
        setResumeMatchError('Could not analyze your resume right now.');
      }
    } finally {
      setResumeMatchLoading(false);
    }
  };

  const handleResumeMatchAction = async (action) => {
    if (!opportunity?.id || resumeMatchActionLoading || resumeMatchAiLoading || resumeMatchLoading) {
      return;
    }

    try {
      const startedAt = Date.now();
      setResumeMatchActionLoading(action);
      setResumeMatchActionError('');
      const data = await generateResumeMatchAction(opportunity.id, action);
      await waitForMinimumDelay(startedAt);
      if (data?.status === 'fallback') {
        setResumeMatchActionError(data?.error || 'Could not run this AI action right now.');
        return;
      }
      setResumeMatchActionResults((previous) => [
        ...previous,
        {
          id: `${action}-${Date.now()}`,
          action,
          data,
        },
      ]);
    } catch (error) {
      console.log('Failed to run resume match action', error);
      setResumeMatchActionError(
        error?.response?.data?.detail || 'Could not run this AI action right now.',
      );
    } finally {
      setResumeMatchActionLoading('');
    }
  };

  const handleGenerateResumeMatchAnalysis = async () => {
    if (!opportunity?.id || resumeMatchAiLoading) {
      return;
    }

    try {
      const startedAt = Date.now();
      setResumeMatchAiLoading(true);
      setResumeMatchAiError('');

      const data = await generateResumeMatchAnalysis(opportunity.id);
      await waitForMinimumDelay(startedAt);
      setResumeMatchAiAnalysis(data);
    } catch (error) {
      console.log('Failed to generate resume match analysis', error);
      setResumeMatchAiError(
        error?.response?.data?.detail || 'Could not generate the full AI analysis right now.',
      );
    } finally {
      setResumeMatchAiLoading(false);
    }
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

          <section className="rounded-md border border-emerald-100 bg-emerald-50 p-5">
            <h3 className="text-xl font-semibold tracking-normal text-emerald-950">
              Is your resume a good match?
            </h3>
            <p className="mt-2 text-sm leading-6 text-emerald-900">
              Use AI to find out how well the skills on your resume fit this job description.
            </p>
            <Button
              type="button"
              className="mt-4 justify-center bg-emerald-800 hover:bg-emerald-900"
              onClick={handleResumeMatch}
            >
              <Sparkles className="h-4 w-4" />
              Get insights
            </Button>
          </section>

          {viewModel.recommendation ? (
            <RecommendationInsightPanel recommendation={viewModel.recommendation} context="detail" />
          ) : null}

          {showResumeMatch ? (
            <ResumeMatchPanel
              resumeMatch={resumeMatch}
              loading={resumeMatchLoading}
              error={resumeMatchError}
              aiAnalysis={resumeMatchAiAnalysis}
              aiLoading={resumeMatchAiLoading}
              aiError={resumeMatchAiError}
              actionResults={resumeMatchActionResults}
              actionLoading={resumeMatchActionLoading}
              actionError={resumeMatchActionError}
              onClose={() => setShowResumeMatch(false)}
              onGenerateAnalysis={handleGenerateResumeMatchAnalysis}
              onAction={handleResumeMatchAction}
            />
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
