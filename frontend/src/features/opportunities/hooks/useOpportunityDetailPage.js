import { useEffect, useMemo, useRef, useState } from 'react';

import {
  FETCHING_SKELETON_MIN_VISIBLE_MS,
} from '../constants/opportunityBrowse.js';
import { DETAIL_SIMILAR_OPPORTUNITIES_LIMIT } from '../constants/opportunityDetail.js';
import {
  getOpportunityById,
  getSimilarOpportunities,
} from '../services/opportunitiesService.js';
import { buildOpportunityDetailPageViewModel } from '../viewModels/opportunityDetail.vm.js';

const SAVED_OPPORTUNITY_IDS_KEY = 'bidwise:saved-opportunity-ids:v1';

const readSavedOpportunityIds = () => {
  if (typeof window === 'undefined') return new Set();

  try {
    const raw = window.localStorage.getItem(SAVED_OPPORTUNITY_IDS_KEY);
    if (!raw) return new Set();

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();

    return new Set(parsed.map((item) => String(item)));
  } catch {
    return new Set();
  }
};

const writeSavedOpportunityIds = (idsSet) => {
  if (typeof window === 'undefined') return;

  window.localStorage.setItem(SAVED_OPPORTUNITY_IDS_KEY, JSON.stringify(Array.from(idsSet)));
};

export const useOpportunityDetailPage = ({ opportunityId, isUserAuthenticated }) => {
  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [similarOpportunities, setSimilarOpportunities] = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState(null);
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [showAllSkills, setShowAllSkills] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const detailLoadingStartedAtRef = useRef(0);
  const detailLoadingHideTimeoutRef = useRef(null);

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
  }, [opportunity?.id]);

  useEffect(() => {
    if (!opportunity?.id || !isUserAuthenticated) {
      setIsSaved(false);
      return;
    }

    const savedIds = readSavedOpportunityIds();
    setIsSaved(savedIds.has(String(opportunity.id)));
  }, [opportunity?.id, isUserAuthenticated]);

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

  const handleApply = () => {
    if (!isUserAuthenticated || !viewModel?.sourceUrl) return;

    window.open(viewModel.sourceUrl, '_blank', 'noopener,noreferrer');
  };

  const handleSave = () => {
    if (!isUserAuthenticated || !opportunity?.id) return;

    const savedIds = readSavedOpportunityIds();
    const normalizedId = String(opportunity.id);
    const nextSaved = !savedIds.has(normalizedId);

    if (nextSaved) {
      savedIds.add(normalizedId);
    } else {
      savedIds.delete(normalizedId);
    }

    writeSavedOpportunityIds(savedIds);
    setIsSaved(nextSaved);
  };

  return {
    loading,
    error,
    viewModel,
    similarLoading,
    similarError,
    isDescriptionExpanded,
    showAllSkills,
    isSaved,
    canApply: isUserAuthenticated && Boolean(viewModel?.sourceUrl),
    toggleDescription: () => setIsDescriptionExpanded((previous) => !previous),
    toggleSkills: () => setShowAllSkills((previous) => !previous),
    handleApply,
    handleSave,
  };
};

export default useOpportunityDetailPage;
