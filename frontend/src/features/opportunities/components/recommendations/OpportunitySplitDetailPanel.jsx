import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { DETAIL_SIMILAR_OPPORTUNITIES_LIMIT } from '../../constants/opportunityDetail.js';
import {
  confirmProfileResume,
  deleteProfileResume,
  generateResumeMatchAction,
  generateResumeMatchAnalysis,
  getResumeMatch,
  getSimilarOpportunities,
  uploadProfileResume,
} from '../../services/opportunitiesService.js';
import { validateResumeFile } from '../../../profile/profileValidation.js';
import { useOpportunityAssistantChat } from '../../hooks/useOpportunityAssistantChat.js';
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
const RESUME_READY_POLL_INTERVAL_MS = 2500;
const RESUME_READY_MAX_POLLS = 72;

const waitForMinimumDelay = async (startedAt, minimumDelay = RESUME_MATCH_MIN_THINKING_MS) => {
  const elapsed = Date.now() - startedAt;
  const remaining = Math.max(0, minimumDelay - elapsed);
  if (remaining > 0) {
    await new Promise((resolve) => {
      window.setTimeout(resolve, remaining);
    });
  }
};

const waitForResumeMatchReady = async (opportunityId, expectedResumeId = null) => {
  let latestMatch = null;

  for (let attempt = 0; attempt < RESUME_READY_MAX_POLLS; attempt += 1) {
    latestMatch = await getResumeMatch(opportunityId);
    const activeResumeId = latestMatch?.evidence?.resume?.id ?? latestMatch?.resume?.id ?? null;
    const expectedResumeIsActive =
      !expectedResumeId || String(activeResumeId || '') === String(expectedResumeId);

    if (expectedResumeIsActive && latestMatch?.has_resume !== false && latestMatch?.status === 'READY') {
      return latestMatch;
    }

    await new Promise((resolve) => {
      window.setTimeout(resolve, RESUME_READY_POLL_INTERVAL_MS);
    });
  }

  return latestMatch;
};

const OpportunitySplitDetailPanel = ({ opportunity, isUserAuthenticated }) => {
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [showAllSkills, setShowAllSkills] = useState(false);
  const [similarOpportunities, setSimilarOpportunities] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState(null);
  const [showResumeMatch, setShowResumeMatch] = useState(false);
  const [resumeMatchOpportunityId, setResumeMatchOpportunityId] = useState(null);
  const [resumeMatch, setResumeMatch] = useState(null);
  const [resumeMatchLoading, setResumeMatchLoading] = useState(false);
  const [resumeMatchError, setResumeMatchError] = useState('');
  const [resumeMatchAiAnalysis, setResumeMatchAiAnalysis] = useState(null);
  const [resumeMatchAiLoading, setResumeMatchAiLoading] = useState(false);
  const [resumeMatchAiError, setResumeMatchAiError] = useState('');
  const [resumeMatchActionResults, setResumeMatchActionResults] = useState([]);
  const [resumeMatchActionLoading, setResumeMatchActionLoading] = useState('');
  const [resumeMatchActionError, setResumeMatchActionError] = useState('');
  const [resumeUploadState, setResumeUploadState] = useState({ status: 'idle', resume: null, error: '' });
  const scrollContainerRef = useRef(null);
  const resumeMatchRequestIdRef = useRef(0);
  const opportunityIdRef = useRef(opportunity?.id);
  opportunityIdRef.current = opportunity?.id;
  const opportunityAssistant = useOpportunityAssistantChat(opportunity?.id);

  useEffect(() => {
    resumeMatchRequestIdRef.current += 1;
    setIsDescriptionExpanded(false);
    setShowAllSkills(false);
    setShowResumeMatch(false);
    setResumeMatchOpportunityId(null);
    setResumeMatch(null);
    setResumeMatchLoading(false);
    setResumeMatchError('');
    setResumeMatchAiAnalysis(null);
    setResumeMatchAiLoading(false);
    setResumeMatchAiError('');
    setResumeMatchActionResults([]);
    setResumeMatchActionLoading('');
    setResumeMatchActionError('');
    setResumeUploadState({ status: 'idle', resume: null, error: '' });
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

  const runResumeMatchAiAnalysis = async (
    startedAt = Date.now(),
    requestId = resumeMatchRequestIdRef.current,
  ) => {
    try {
      setResumeMatchLoading(true);
      const data = await generateResumeMatchAnalysis(opportunity.id);
      await waitForMinimumDelay(startedAt);
      if (requestId !== resumeMatchRequestIdRef.current) return;
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
      if (requestId !== resumeMatchRequestIdRef.current) return;
      console.log('Failed to generate resume match analysis', error);

      try {
        const fallbackStartedAt = Date.now();
        const fallback = await getResumeMatch(opportunity.id);
        await waitForMinimumDelay(fallbackStartedAt, 500);
        if (requestId !== resumeMatchRequestIdRef.current) return;
        setResumeMatch(fallback);
        setResumeMatchAiError(
          error?.response?.data?.detail || 'The full AI analysis is not available right now. Showing the quick BidWise analysis instead.',
        );
      } catch (fallbackError) {
        console.log('Failed to load resume match fallback', fallbackError);
        setResumeMatchError('Could not analyze your resume right now.');
      }
    } finally {
      if (requestId === resumeMatchRequestIdRef.current) {
        setResumeMatchLoading(false);
      }
    }
  };

  const handleResumeMatch = async () => {
    if (!opportunity?.id) {
      return;
    }

    const requestId = resumeMatchRequestIdRef.current + 1;
    resumeMatchRequestIdRef.current = requestId;
    setResumeMatchError('');
    setResumeMatch(null);
    setResumeMatchAiAnalysis(null);
    setResumeMatchAiError('');
    setResumeMatchActionResults([]);
    setResumeMatchActionLoading('');
    setResumeMatchActionError('');
    setResumeUploadState({ status: 'idle', resume: null, error: '' });
    setResumeMatchOpportunityId(opportunity.id);
    setResumeMatchLoading(true);
    setShowResumeMatch(true);

    try {
      const startedAt = Date.now();
      const initialMatch = await getResumeMatch(opportunity.id);
      if (requestId !== resumeMatchRequestIdRef.current) return;
      setResumeMatch(initialMatch);

      if (initialMatch?.has_resume === false || initialMatch?.status !== 'READY') {
        return;
      }

      await runResumeMatchAiAnalysis(startedAt, requestId);
    } catch (error) {
      if (requestId !== resumeMatchRequestIdRef.current) return;
      console.log('Failed to generate resume match analysis', error);

      try {
        const fallbackStartedAt = Date.now();
        const fallback = await getResumeMatch(opportunity.id);
        await waitForMinimumDelay(fallbackStartedAt, 500);
        if (requestId !== resumeMatchRequestIdRef.current) return;
        setResumeMatch(fallback);
        setResumeMatchAiError(
          error?.response?.data?.detail || 'The full AI analysis is not available right now. Showing the quick BidWise analysis instead.',
        );
      } catch (fallbackError) {
        console.log('Failed to load resume match fallback', fallbackError);
        setResumeMatchError('Could not analyze your resume right now.');
      }
    } finally {
      if (requestId === resumeMatchRequestIdRef.current) {
        setResumeMatchLoading(false);
      }
    }
  };

  const handleResumeMatchAction = async (action) => {
    if (!opportunity?.id || resumeMatchActionLoading || resumeMatchAiLoading || resumeMatchLoading) {
      return;
    }

    const requestOpportunityId = opportunity.id;
    const requestId = resumeMatchRequestIdRef.current;

    try {
      const startedAt = Date.now();
      setResumeMatchActionLoading(action);
      setResumeMatchActionError('');
      const data = await generateResumeMatchAction(opportunity.id, action);
      await waitForMinimumDelay(startedAt);
      if (
        requestId !== resumeMatchRequestIdRef.current ||
        requestOpportunityId !== opportunityIdRef.current
      ) {
        return;
      }
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
      if (
        requestId !== resumeMatchRequestIdRef.current ||
        requestOpportunityId !== opportunityIdRef.current
      ) {
        return;
      }
      console.log('Failed to run resume match action', error);
      setResumeMatchActionError(
        error?.response?.data?.detail || 'Could not run this AI action right now.',
      );
    } finally {
      if (
        requestId === resumeMatchRequestIdRef.current &&
        requestOpportunityId === opportunityIdRef.current
      ) {
        setResumeMatchActionLoading('');
      }
    }
  };

  const handleResumeUpload = async (file) => {
    const validationError = validateResumeFile(file);
    if (validationError) {
      setResumeUploadState({ status: 'idle', resume: null, error: validationError });
      return;
    }

    try {
      setResumeUploadState({ status: 'uploading', resume: null, error: '' });
      const data = await uploadProfileResume(file);
      setResumeUploadState({ status: 'confirm', resume: data?.resume || null, error: '' });
    } catch (error) {
      console.log('Failed to upload resume from assistant', error);
      setResumeUploadState({
        status: 'idle',
        resume: null,
        error: error?.response?.data?.file?.[0] || error?.response?.data?.detail || 'Resume upload failed.',
      });
    }
  };

  const handleCancelResumeUpload = async () => {
    const resumeId = resumeUploadState.resume?.id;
    setResumeUploadState({ status: 'idle', resume: null, error: '' });
    if (!resumeId) return;

    try {
      await deleteProfileResume(resumeId);
    } catch (error) {
      console.log('Failed to cancel resume upload from assistant', error);
    }
  };

  const handleConfirmResumeUpload = async () => {
    const resumeId = resumeUploadState.resume?.id;
    if (!resumeId) return;
    const requestId = resumeMatchRequestIdRef.current + 1;
    resumeMatchRequestIdRef.current = requestId;

    try {
      setResumeUploadState((previous) => ({ ...previous, status: 'confirming', error: '' }));
      const data = await confirmProfileResume(resumeId);
      setResumeUploadState({ status: 'processing', resume: data?.resume || resumeUploadState.resume, error: '' });
      setResumeMatch({
        has_resume: true,
        status: 'PROCESSING',
        can_generate_ai_analysis: false,
      });
      setResumeMatchError('');
      setResumeMatchAiAnalysis(null);
      setResumeMatchAiError('');
      setResumeMatchActionResults([]);
      setResumeMatchActionLoading('');
      setResumeMatchActionError('');
      setResumeMatchLoading(true);

      const readyMatch = await waitForResumeMatchReady(opportunity.id, resumeId);
      if (requestId !== resumeMatchRequestIdRef.current) return;
      if (readyMatch?.status !== 'READY') {
        const activeResumeId = readyMatch?.evidence?.resume?.id ?? readyMatch?.resume?.id ?? null;
        const expectedResumeIsActive = String(activeResumeId || '') === String(resumeId);
        setResumeMatch(expectedResumeIsActive && readyMatch ? readyMatch : {
          has_resume: true,
          status: 'PROCESSING',
          can_generate_ai_analysis: false,
        });
        setResumeUploadState((previous) => ({
          ...previous,
          status: 'idle',
          error: 'Resume analysis is still running. Please try again in a moment.',
        }));
        setResumeMatchError('Resume analysis is still running. Please try again in a moment.');
        setResumeMatchLoading(false);
        return;
      }

      setResumeMatch(readyMatch);
      setResumeUploadState({ status: 'idle', resume: readyMatch?.resume || data?.resume || resumeUploadState.resume, error: '' });
      localStorage.setItem('bidwise_resume_updated_at', String(Date.now()));
      window.dispatchEvent(
        new CustomEvent('bidwise:resume-updated', {
          detail: { resume: data?.resume || resumeUploadState.resume || null },
        }),
      );
      await runResumeMatchAiAnalysis(Date.now(), requestId);
    } catch (error) {
      console.log('Failed to confirm resume from assistant', error);
      setResumeMatchLoading(false);
      setResumeUploadState((previous) => ({
        ...previous,
        status: 'confirm',
        error: error?.response?.data?.detail || 'Could not activate the resume.',
      }));
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

          {showResumeMatch && resumeMatchOpportunityId === opportunity.id ? (
            <ResumeMatchPanel
              key={opportunity.id}
              resumeMatch={resumeMatch}
              loading={resumeMatchLoading}
              error={resumeMatchError}
              aiAnalysis={resumeMatchAiAnalysis}
              aiLoading={resumeMatchAiLoading}
              aiError={resumeMatchAiError}
              actionResults={resumeMatchActionResults}
              actionLoading={resumeMatchActionLoading}
              actionError={resumeMatchActionError}
              uploadState={resumeUploadState}
              onClose={() => setShowResumeMatch(false)}
              onGenerateAnalysis={handleGenerateResumeMatchAnalysis}
              onAction={handleResumeMatchAction}
              onUploadResume={handleResumeUpload}
              onCancelResumeUpload={handleCancelResumeUpload}
              onConfirmResumeUpload={handleConfirmResumeUpload}
              chatMessages={opportunityAssistant.messages}
              chatLoading={opportunityAssistant.loading}
              chatError={opportunityAssistant.error}
              onSendQuestion={opportunityAssistant.sendQuestion}
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
