import { useEffect, useMemo, useRef, useState } from 'react';

import {
  FETCHING_SKELETON_MIN_VISIBLE_MS,
} from '../constants/opportunityBrowse.js';
import { DETAIL_SIMILAR_OPPORTUNITIES_LIMIT } from '../constants/opportunityDetail.js';
import {
  getOpportunityById,
  registerExternalApplicationClick,
  listOpportunityRecommendations,
  getSimilarOpportunities,
  updateExternalApplicationStatus,
} from '../services/opportunitiesService.js';
import { mergeRecommendationIntoOpportunity } from '../utils/recommendationUtils.js';
import {
  clearPendingExternalApplication,
  getPendingExternalApplicationForOpportunity,
  postponePendingExternalApplication,
  upsertPendingExternalApplication,
} from '../utils/externalApplicationTracking.js';
import {
  isOpportunitySaved,
  toggleSavedOpportunity,
} from '../utils/savedOpportunityStorage.js';
import { buildOpportunityDetailPageViewModel } from '../viewModels/opportunityDetail.vm.js';

const EXTERNAL_CONFIRMED_STATUS = 'EXTERNAL_APPLIED_CONFIRMED';
const EXTERNAL_TRACKED_PENDING_STATUSES = new Set([
  'EXTERNAL_CLICKED',
  'EXTERNAL_REMIND_LATER',
  'POSTULEE_EXTERNEMENT',
  'VUE',
  'INTERESSEE',
  'ABANDONNEE',
]);
const INTERNAL_APPLIED_STATUSES = new Set([
  'SUBMITTED',
  'VIEWED_BY_ORGANIZATION',
  'REJECTED',
  'WITHDRAWN',
]);
const EXTERNAL_RETURN_PROMPT_DELAY_MS = 2 * 1000;

export const useOpportunityDetailPage = ({ opportunityId, isUserAuthenticated }) => {
  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [similarOpportunities, setSimilarOpportunities] = useState([]);
  const [recommendation, setRecommendation] = useState(null);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [recommendationError, setRecommendationError] = useState(null);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState(null);
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [showAllSkills, setShowAllSkills] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isApplied, setIsApplied] = useState(false);
  const [isApplyingExternally, setIsApplyingExternally] = useState(false);
  const [externalPromptOpen, setExternalPromptOpen] = useState(false);
  const [externalPromptError, setExternalPromptError] = useState('');
  const [externalPromptBusy, setExternalPromptBusy] = useState(false);
  const [pendingExternalApplication, setPendingExternalApplication] = useState(null);
  const detailLoadingStartedAtRef = useRef(0);
  const detailLoadingHideTimeoutRef = useRef(null);
  const externalPromptTimeoutRef = useRef(null);

  useEffect(() => {
    let isCancelled = false;

    if (!opportunityId) {
      if (detailLoadingHideTimeoutRef.current) {
        clearTimeout(detailLoadingHideTimeoutRef.current);
        detailLoadingHideTimeoutRef.current = null;
      }

      detailLoadingStartedAtRef.current = 0;
      setOpportunity(null);
      setLoading(false);
      setError('Opportunity id is missing.');

      return undefined;
    }

    const fetchOpportunity = async () => {
      try {
        if (detailLoadingHideTimeoutRef.current) {
          clearTimeout(detailLoadingHideTimeoutRef.current);
          detailLoadingHideTimeoutRef.current = null;
        }

        detailLoadingStartedAtRef.current = Date.now();
        setLoading(true);
        setError('');

        const data = await getOpportunityById(opportunityId);
        if (isCancelled) return;

        setOpportunity(data ?? null);
      } catch (err) {
        if (isCancelled) return;

        const message = err?.response?.data?.detail || 'Unable to load this opportunity. Please try again.';
        setError(message);
        setOpportunity(null);
      } finally {
        if (isCancelled) return;

        const elapsedVisibleMs = Date.now() - (detailLoadingStartedAtRef.current || Date.now());
        const remainingVisibleMs = FETCHING_SKELETON_MIN_VISIBLE_MS - elapsedVisibleMs;

        if (remainingVisibleMs <= 0) {
          detailLoadingStartedAtRef.current = 0;
          setLoading(false);
          return;
        }

        detailLoadingHideTimeoutRef.current = setTimeout(() => {
          detailLoadingHideTimeoutRef.current = null;
          if (isCancelled) return;

          detailLoadingStartedAtRef.current = 0;
          setLoading(false);
        }, remainingVisibleMs);
      }
    };

    fetchOpportunity();

    return () => {
      isCancelled = true;
      if (detailLoadingHideTimeoutRef.current) {
        clearTimeout(detailLoadingHideTimeoutRef.current);
        detailLoadingHideTimeoutRef.current = null;
      }
    };
  }, [opportunityId]);

  useEffect(() => {
    setIsDescriptionExpanded(false);
    setShowAllSkills(false);
    const currentStatus = String(opportunity?.my_application?.status || '').trim();
    setIsApplied(
      INTERNAL_APPLIED_STATUSES.has(currentStatus)
      || currentStatus === EXTERNAL_CONFIRMED_STATUS,
    );
  }, [opportunity?.id]);

  useEffect(() => {
    if (!opportunity?.id || !isUserAuthenticated) {
      setIsSaved(false);
      return;
    }

    setIsSaved(isOpportunitySaved(opportunity.id));
  }, [opportunity?.id, isUserAuthenticated]);

  useEffect(() => {
    if (externalPromptTimeoutRef.current) {
      clearTimeout(externalPromptTimeoutRef.current);
      externalPromptTimeoutRef.current = null;
    }

    if (!opportunity?.id || !isUserAuthenticated) {
      setPendingExternalApplication(null);
      setExternalPromptOpen(false);
      setExternalPromptError('');
      return undefined;
    }

    const maybeOpenPrompt = () => {
      const latest = getPendingExternalApplicationForOpportunity(opportunity.id);
      if (!latest) {
        setPendingExternalApplication(null);
        setExternalPromptOpen(false);
        return;
      }

      const backendStatus = String(opportunity?.my_application?.status || '').trim();
      if (backendStatus === EXTERNAL_CONFIRMED_STATUS) {
        clearPendingExternalApplication(latest.applicationId);
        setPendingExternalApplication(null);
        setExternalPromptOpen(false);
        return;
      }

      setPendingExternalApplication(latest);

      if (document.visibilityState !== 'visible') return;

      const remainingDelay = (latest.remindAfter || 0) - Date.now();
      if (remainingDelay > 0) {
        externalPromptTimeoutRef.current = setTimeout(maybeOpenPrompt, remainingDelay);
        return;
      }

      if (
        latest.applicationId
        && (
          EXTERNAL_TRACKED_PENDING_STATUSES.has(backendStatus)
          || backendStatus === ''
        )
      ) {
        setPendingExternalApplication(latest);
        setExternalPromptOpen(true);
      }
    };

    const handleVisibilityOrFocus = () => {
      if (document.visibilityState === 'visible') {
        maybeOpenPrompt();
      }
    };

    handleVisibilityOrFocus();
    window.addEventListener('focus', handleVisibilityOrFocus);
    document.addEventListener('visibilitychange', handleVisibilityOrFocus);

    maybeOpenPrompt();

    return () => {
      window.removeEventListener('focus', handleVisibilityOrFocus);
      document.removeEventListener('visibilitychange', handleVisibilityOrFocus);
      if (externalPromptTimeoutRef.current) {
        clearTimeout(externalPromptTimeoutRef.current);
        externalPromptTimeoutRef.current = null;
      }
    };
  }, [
    isUserAuthenticated,
    opportunity?.id,
    opportunity?.my_application?.status,
    pendingExternalApplication?.applicationId,
    pendingExternalApplication?.remindAfter,
  ]);

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
      } catch (err) {
        if (isCancelled) return;

        console.log('Failed to load similar opportunities', err);
        setSimilarError(err);
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

  useEffect(() => {
    let isCancelled = false;

    if (!isUserAuthenticated || !opportunity?.id) {
      setRecommendation(null);
      setRecommendationLoading(false);
      setRecommendationError(null);
      return undefined;
    }

    const fetchRecommendation = async () => {
      try {
        setRecommendationLoading(true);
        setRecommendationError(null);

        const data = await listOpportunityRecommendations({ limit: 50 });
        if (isCancelled) return;

        const matchedRecommendation = data.find(
          (item) => String(item?.id) === String(opportunity.id),
        );
        setRecommendation(matchedRecommendation || null);
      } catch (err) {
        if (isCancelled) return;
        console.log('Failed to load recommendation insight', err);
        setRecommendationError(err);
        setRecommendation(null);
      } finally {
        if (!isCancelled) {
          setRecommendationLoading(false);
        }
      }
    };

    fetchRecommendation();

    return () => {
      isCancelled = true;
    };
  }, [isUserAuthenticated, opportunity?.id]);

  const viewModel = useMemo(
    () =>
      buildOpportunityDetailPageViewModel({
        opportunity: recommendation
          ? mergeRecommendationIntoOpportunity(opportunity, recommendation)
          : opportunity,
        isUserAuthenticated,
        similarOpportunities,
        showAllSkills,
      }),
    [isUserAuthenticated, opportunity, recommendation, showAllSkills, similarOpportunities],
  );

  const handleApply = async () => {
    if (!isUserAuthenticated || !viewModel?.sourceUrl || !opportunity?.id) return;

    setExternalPromptError('');

    if (viewModel.acceptsDirectApplications) {
      return;
    }

    setIsApplyingExternally(true);
    try {
      const result = await registerExternalApplicationClick(opportunity.id);
      const nextPending = upsertPendingExternalApplication({
        applicationId: result.application_id,
        opportunityId: opportunity.id,
        title: viewModel.title,
        organizationLabel: viewModel.organizationLabel,
        sourceUrl: viewModel.sourceUrl,
        clickedAt: Date.now(),
        remindAfter: Date.now() + EXTERNAL_RETURN_PROMPT_DELAY_MS,
      });
      setPendingExternalApplication(nextPending);
    } catch (error) {
      console.log('Unable to save external application tracking', error);
    } finally {
      window.open(viewModel.sourceUrl, '_blank', 'noopener,noreferrer');
      setIsApplyingExternally(false);
    }
  };

  const handleExternalApplicationConfirmed = async () => {
    if (!pendingExternalApplication?.applicationId) return;

    try {
      setExternalPromptBusy(true);
      setExternalPromptError('');
      await updateExternalApplicationStatus(
        pendingExternalApplication.applicationId,
        EXTERNAL_CONFIRMED_STATUS,
      );
      clearPendingExternalApplication(pendingExternalApplication.applicationId);
      setPendingExternalApplication(null);
      setExternalPromptOpen(false);
      setIsApplied(true);
    } catch (error) {
      const message = error?.response?.data?.detail || 'Unable to update your external application status.';
      setExternalPromptError(message);
    } finally {
      setExternalPromptBusy(false);
    }
  };

  const handleExternalApplicationNotYet = () => {
    if (!pendingExternalApplication?.applicationId) {
      setExternalPromptOpen(false);
      return;
    }

    clearPendingExternalApplication(pendingExternalApplication.applicationId);
    setPendingExternalApplication(null);
    setExternalPromptError('');
    setExternalPromptOpen(false);
  };

  const handleExternalApplicationRemindLater = async () => {
    if (!pendingExternalApplication?.applicationId) return;

    try {
      setExternalPromptBusy(true);
      setExternalPromptError('');
      await updateExternalApplicationStatus(
        pendingExternalApplication.applicationId,
        'EXTERNAL_REMIND_LATER',
      );
      const nextPending = postponePendingExternalApplication(
        pendingExternalApplication.applicationId,
        'remind_later',
      );
      setPendingExternalApplication(nextPending);
      setExternalPromptOpen(false);
    } catch (error) {
      const message = error?.response?.data?.detail || 'Unable to save your reminder preference.';
      setExternalPromptError(message);
    } finally {
      setExternalPromptBusy(false);
    }
  };

  const handleSave = () => {
    if (!isUserAuthenticated || !opportunity?.id) return;

    const nextSaved = toggleSavedOpportunity(opportunity.id);
    setIsSaved(nextSaved);
  };

  return {
    loading,
    error,
    viewModel,
    recommendationLoading,
    recommendationError,
    similarLoading,
    similarError,
    isDescriptionExpanded,
    showAllSkills,
    isSaved,
    isApplied,
    isApplyingExternally,
    externalPromptOpen,
    externalPromptError,
    externalPromptBusy,
    pendingExternalApplication,
    canApply:
      isUserAuthenticated
      && !isApplied
      && Boolean(viewModel?.acceptsDirectApplications || viewModel?.sourceUrl),
    toggleDescription: () => setIsDescriptionExpanded((previous) => !previous),
    toggleSkills: () => setShowAllSkills((previous) => !previous),
    handleApply,
    handleSave,
    markApplied: () => setIsApplied(true),
    closeExternalPrompt: () => {
      if (pendingExternalApplication?.applicationId) {
        clearPendingExternalApplication(pendingExternalApplication.applicationId);
        setPendingExternalApplication(null);
      }
      setExternalPromptError('');
      setExternalPromptOpen(false);
    },
    handleExternalApplicationConfirmed,
    handleExternalApplicationNotYet,
    handleExternalApplicationRemindLater,
  };
};

export default useOpportunityDetailPage;
