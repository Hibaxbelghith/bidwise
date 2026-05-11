import {
  DESCRIPTION_LONG_THRESHOLD,
  QUICK_SCAN_SKILLS_LIMIT,
} from '../constants/opportunityDetail.js';
import {
  buildDescriptionMarkup,
  buildDescriptionText,
  formatDate,
  formatExperienceLabel,
  formatOrganizationLabel,
  getCompanyLogoAsset,
  getOpportunityStatusLabel,
  getOpportunityTypeLabel,
} from '../utils/opportunityFormatters.js';
import {
  buildAdditionalInfoItems,
  buildAIDraft,
  buildMatchBullets,
  dedupeSimilarOpportunities,
  getLanguagePreview,
  getProjectDocuments,
  getSemanticMatchScore,
  getSkills,
} from '../utils/opportunityHelpers.js';

const getExtraData = (opportunity) =>
  opportunity?.extra_data && typeof opportunity.extra_data === 'object' ? opportunity.extra_data : {};

const getStructuredProjectData = (extraData) =>
  extraData?.structured && typeof extraData.structured === 'object' ? extraData.structured : {};

const getProjectLots = (extraData) => (Array.isArray(extraData.lots) ? extraData.lots.filter(Boolean) : []);

const getProjectCautionLabel = (extraData, projectLots) =>
  String(
    extraData.caution ||
      projectLots.find((lot) => String(lot?.caution || '').trim())?.caution ||
      '',
  ).trim();

const getRecommendationPayload = (opportunity) => {
  const payload = opportunity?.recommendation || opportunity;
  if (!payload) return null;
  const rawScore = payload.score ?? payload.match_score;
  const hasRecommendationSignal = Boolean(
    payload.score_label ||
      payload.recommendation_confidence ||
      payload.recommendation_mode ||
      (rawScore !== null && rawScore !== undefined && rawScore !== '' && Number.isFinite(Number(rawScore))),
  );

  return hasRecommendationSignal ? payload : null;
};

export const buildOpportunityDetailViewModel = (opportunity) => {
  if (!opportunity) return null;

  const extraData = getExtraData(opportunity);
  const structuredProjectData = getStructuredProjectData(extraData);
  const projectLots = getProjectLots(extraData);
  const projectDocuments = getProjectDocuments(opportunity);
  const descriptionText = buildDescriptionText(opportunity);
  const isProject = opportunity.type_opportunite === 'PROJET';

  return {
    id: opportunity.id,
    title: opportunity.titre || 'Untitled opportunity',
    typeLabel: getOpportunityTypeLabel(opportunity.type_opportunite),
    statusLabel: getOpportunityStatusLabel(opportunity.statut),
    statusBadgeVariant: opportunity?.statut === 'ACTIVE' ? 'default' : 'outline',
    organizationLabel: formatOrganizationLabel(opportunity),
    sourceName: String(opportunity.source?.nom || '').trim(),
    sourceUrl: String(opportunity.source_item_url || '').trim(),
    publishedDateLabel: formatDate(opportunity.date_publication),
    deadlineDateLabel: opportunity.date_limite ? formatDate(opportunity.date_limite) : '',
    descriptionMarkup: buildDescriptionMarkup(opportunity),
    descriptionText,
    isLongDescription: descriptionText.length > DESCRIPTION_LONG_THRESHOLD,
    isProject,
    extraData,
    hasExtraData: Object.keys(extraData).length > 0,
    projectLots,
    projectDocuments,
    hasProjectDocuments: Boolean(extraData.has_pdf) || projectDocuments.length > 0,
    salaryLabel: String(opportunity.salary || '').trim(),
    locationLabel: String(opportunity.ville || '').trim(),
    projectRegionLabel: String(extraData.region || extraData.region_execution || opportunity.ville || '').trim(),
    contractLabel: String(opportunity.contract_type || '').trim(),
    availabilityLabel: String(opportunity.availability || '').trim(),
    educationLabel: String(opportunity.education_level || '').trim(),
    experienceLabel: formatExperienceLabel(opportunity),
    projectProcedureLabel: String(structuredProjectData.procedure || extraData.procedure || '').trim(),
    projectFinancementLabel: String(structuredProjectData.financement || extraData.financement || '').trim(),
    projectTypeCommandeLabel: String(structuredProjectData.type_commande || extraData.type_commande || '').trim(),
    projectDelaiValiditeLabel: String(
      structuredProjectData.delai_validite || extraData.delai_validite || '',
    ).trim(),
    projectCautionLabel: getProjectCautionLabel(extraData, projectLots),
    primaryActionLabel: isProject ? 'Open source' : 'Apply',
    companyLogo: getCompanyLogoAsset(opportunity),
    skills: getSkills(opportunity),
    languagesLabel: getLanguagePreview(opportunity, 3).join(', '),
  };
};

export const buildOpportunityDetailPageViewModel = ({
  opportunity,
  isUserAuthenticated,
  similarOpportunities,
  showAllSkills,
}) => {
  const detail = buildOpportunityDetailViewModel(opportunity);
  if (!detail) return null;

  const dedupedSimilar = !isUserAuthenticated
    ? []
    : dedupeSimilarOpportunities(similarOpportunities).filter(
        (item) => Number(item?.id) !== Number(detail.id),
      );
  const semanticMatchScore = isUserAuthenticated ? getSemanticMatchScore(dedupedSimilar) : null;

  return {
    ...detail,
    additionalInfoItems: detail.hasExtraData ? buildAdditionalInfoItems(detail.extraData) : [],
    visibleSkills: showAllSkills ? detail.skills : detail.skills.slice(0, QUICK_SCAN_SKILLS_LIMIT),
    hiddenSkillsCount: Math.max(0, detail.skills.length - QUICK_SCAN_SKILLS_LIMIT),
    displayLocationLabel: detail.isProject ? detail.projectRegionLabel : detail.locationLabel,
    snapshotProps: {
      sourceName: detail.sourceName,
      isProject: detail.isProject,
      typeLabel: detail.typeLabel,
      projectRegionLabel: detail.projectRegionLabel,
      projectProcedureLabel: detail.projectProcedureLabel,
      projectFinancementLabel: detail.projectFinancementLabel,
      projectTypeCommandeLabel: detail.projectTypeCommandeLabel,
      projectCautionLabel: detail.projectCautionLabel,
      organizationLabel: detail.organizationLabel,
      contractLabel: detail.contractLabel,
      availabilityLabel: detail.availabilityLabel,
      experienceLabel: detail.experienceLabel,
      educationLabel: detail.educationLabel,
      languagesLabel: detail.languagesLabel,
    },
    dedupedSimilar,
    semanticMatchScore,
    matchBullets: buildMatchBullets(opportunity, semanticMatchScore),
    aiDraft: buildAIDraft(opportunity),
    recommendation: getRecommendationPayload(opportunity),
  };
};
