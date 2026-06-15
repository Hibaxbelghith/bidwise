import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getOpportunityById,
  getSimilarOpportunities,
  type Opportunity,
  type SimilarOpportunity,
} from '../services/opportunitiesService';
import {
  buildAdditionalInfoItems,
  buildMatchBullets,
  computeSemanticMatchScore,
  dedupeSimilarItems,
  dedupeStrings,
  formatDisplayValue,
  getExtraData,
  getLanguagesLabel,
  getProjectDocuments,
  hasDisplayValue,
  wait,
} from '../utils/opportunityHelpers';
import {
  formatDate,
  formatExperienceLabel,
  getOrganizationLabel,
  normalizeDescription,
} from '../utils/opportunityFormatters';
import {
  isOpportunitySaved,
  listenSavedOpportunityChanges,
} from '../utils/savedOpportunitiesStorage';

const MIN_LOADING_TIME_MS = 400;
const QUICK_SCAN_SKILLS_LIMIT = 5;
const SIMILAR_AUTH_LIMIT = 6;

export function useOpportunityDetail({
  idParam,
  isUserAuthenticated,
  onInvalidId,
}: {
  idParam?: string | string[];
  isUserAuthenticated: boolean;
  onInvalidId?: () => void;
}) {
  const [item, setItem] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [similarItems, setSimilarItems] = useState<SimilarOpportunity[]>([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState('');
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [showAllSkills, setShowAllSkills] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const safeId = useMemo(() => {
    if (Array.isArray(idParam)) return idParam[0] || '';
    return String(idParam || '').trim();
  }, [idParam]);

  const hasValidOpportunityId = useMemo(() => /^\d+$/.test(safeId), [safeId]);

  useEffect(() => {
    if (!safeId || hasValidOpportunityId || !onInvalidId) return;
    onInvalidId();
  }, [hasValidOpportunityId, onInvalidId, safeId]);

  const fetchDetail = useCallback(async () => {
    if (!safeId || !hasValidOpportunityId) {
      setError('Invalid opportunity id.');
      setItem(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    const startedAt = Date.now();

    try {
      const data = await getOpportunityById(safeId);
      setItem(data);
      setError('');
    } catch {
      setError('Unable to load this opportunity right now.');
      setItem(null);
    } finally {
      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_LOADING_TIME_MS) {
        await wait(MIN_LOADING_TIME_MS - elapsed);
      }
      setLoading(false);
    }
  }, [hasValidOpportunityId, safeId]);

  useEffect(() => {
    void fetchDetail();
  }, [fetchDetail]);

  useEffect(() => {
    if (!item?.id || !isUserAuthenticated) {
      setSimilarItems([]);
      setSimilarError('');
      setSimilarLoading(false);
      return;
    }

    let cancelled = false;

    const loadSimilar = async () => {
      setSimilarLoading(true);
      setSimilarError('');

      try {
        const data = await getSimilarOpportunities(item.id, SIMILAR_AUTH_LIMIT);
        if (cancelled) return;
        setSimilarItems(Array.isArray(data) ? data : []);
      } catch {
        if (cancelled) return;
        setSimilarItems([]);
        setSimilarError('Unable to load similar opportunities.');
      } finally {
        if (!cancelled) setSimilarLoading(false);
      }
    };

    void loadSimilar();

    return () => {
      cancelled = true;
    };
  }, [item?.id, isUserAuthenticated]);

  useEffect(() => {
    setShowAllSkills(false);
    setIsDescriptionExpanded(false);
  }, [item?.id]);

  useEffect(() => {
    let isMounted = true;

    if (!item?.id || !isUserAuthenticated) {
      setIsSaved(false);
      return undefined;
    }

    const sync = async () => {
      const nextValue = await isOpportunitySaved(item.id);
      if (isMounted) {
        setIsSaved(nextValue);
      }
    };

    void sync();
    const unsubscribe = listenSavedOpportunityChanges(() => {
      void sync();
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [isUserAuthenticated, item?.id]);

  const extraData = useMemo(() => getExtraData(item), [item]);
  const hasExtraData = Object.keys(extraData || {}).length > 0;
  const structuredProjectData = useMemo(() => {
    if (extraData?.structured && typeof extraData.structured === 'object') {
      return extraData.structured as Record<string, unknown>;
    }
    return {};
  }, [extraData]);
  const projectDocuments = useMemo(() => getProjectDocuments(item), [item]);
  const projectLots = useMemo(
    () => (Array.isArray(extraData.lots) ? extraData.lots.filter(Boolean) : []),
    [extraData.lots],
  );
  const additionalInfoItems = useMemo(
    () => (hasExtraData ? buildAdditionalInfoItems(extraData) : []),
    [extraData, hasExtraData],
  );

  const isProject = item?.type_opportunite === 'PROJET';
  const sourceLabel = formatDisplayValue(item?.source?.nom);
  const salaryLabel = formatDisplayValue(item?.salary);
  const contractLabel = formatDisplayValue(item?.contract_type);
  const availabilityLabel = formatDisplayValue(item?.availability);
  const educationLabel = formatDisplayValue(item?.education_level);
  const companyLabel = item ? getOrganizationLabel(item) : '';
  const rawLocationLabel = formatDisplayValue(item?.ville);
  const projectRegionLabel = formatDisplayValue(
    extraData.region || extraData.region_execution || item?.ville,
  );
  const locationLabel = isProject ? projectRegionLabel : rawLocationLabel;
  const projectProcedureLabel = formatDisplayValue(
    structuredProjectData.procedure || extraData.procedure,
  );
  const projectFinancementLabel = formatDisplayValue(
    structuredProjectData.financement || extraData.financement,
  );
  const projectTypeCommandeLabel = formatDisplayValue(
    structuredProjectData.type_commande || extraData.type_commande,
  );
  const projectDelaiValiditeLabel = formatDisplayValue(
    structuredProjectData.delai_validite || extraData.delai_validite,
  );
  const projectCautionLabel = formatDisplayValue(
    extraData.caution || projectLots.find((lot) => hasDisplayValue(lot?.caution))?.caution,
  );
  const description = item ? normalizeDescription(item) : '';
  const skills = item ? dedupeStrings(item.skills) : [];
  const languagesLabel = item ? getLanguagesLabel(item) : '';
  const quickScanSkills = skills.slice(0, QUICK_SCAN_SKILLS_LIMIT);
  const hiddenSkillsCount = Math.max(0, skills.length - quickScanSkills.length);
  const isLongDescription = description.length > 420;
  const tenderFactRows = [
    { icon: '🏢', label: 'Acheteur', value: companyLabel },
    { icon: '📍', label: 'Region', value: projectRegionLabel },
    { icon: '📅', label: 'Date publication', value: item?.date_publication ? formatDate(item.date_publication) : '' },
    { icon: '⏳', label: 'Date limite', value: item?.date_limite ? formatDate(item.date_limite) : '' },
    { icon: '📄', label: 'Procedure', value: projectProcedureLabel },
    { icon: '💰', label: 'Mode financement', value: projectFinancementLabel },
    { icon: '🗂️', label: 'Type commande', value: projectTypeCommandeLabel },
    { icon: '🕒', label: 'Validite offre', value: projectDelaiValiditeLabel },
    { icon: '💸', label: 'Caution', value: projectCautionLabel },
  ].filter((fact) => hasDisplayValue(fact.value));

  const dedupedSimilar = useMemo(
    () => dedupeSimilarItems(similarItems, Number(item?.id || 0)),
    [item?.id, similarItems],
  );
  const semanticScore = isUserAuthenticated ? computeSemanticMatchScore(dedupedSimilar) : null;
  const matchBullets = useMemo(
    () => (item ? buildMatchBullets(item, semanticScore) : []),
    [item, semanticScore],
  );

  return {
    item,
    loading,
    error,
    fetchDetail,
    similarLoading,
    similarError,
    isDescriptionExpanded,
    setIsDescriptionExpanded,
    showAllSkills,
    setShowAllSkills,
    isSaved,
    setIsSaved,
    hasValidOpportunityId,
    isProject,
    extraData,
    hasExtraData,
    projectDocuments,
    projectLots,
    additionalInfoItems,
    sourceLabel,
    salaryLabel,
    contractLabel,
    availabilityLabel,
    educationLabel,
    companyLabel,
    rawLocationLabel,
    projectRegionLabel,
    locationLabel,
    projectProcedureLabel,
    projectFinancementLabel,
    projectTypeCommandeLabel,
    projectDelaiValiditeLabel,
    projectCautionLabel,
    description,
    skills,
    languagesLabel,
    quickScanSkills,
    hiddenSkillsCount,
    isLongDescription,
    tenderFactRows,
    dedupedSimilar,
    semanticScore,
    matchBullets,
  };
}

export default useOpportunityDetail;
