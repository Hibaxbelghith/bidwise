import {
  buildDescriptionPreview,
  formatDate,
  formatExperienceLabel,
  formatRelativeDate,
  formatSimilarityScore,
  getCardAiHint,
  getCompanyLogoAsset,
  getOpportunityStatusLabel,
  getOpportunityTypeLabel,
  formatOrganizationLabel,
} from '../utils/opportunityFormatters.js';
import { getLanguagePreview, getProjectDocuments } from '../utils/opportunityHelpers.js';

const WORK_MODE_LABELS = {
  REMOTE: 'Remote',
  HYBRID: 'Hybrid',
  ON_SITE: 'On site',
};

export const buildOpportunityBrowseCardViewModel = (opportunity, isUserAuthenticated) => {
  const organizationLabel = formatOrganizationLabel(opportunity);
  const extraData = opportunity?.extra_data && typeof opportunity.extra_data === 'object' ? opportunity.extra_data : {};
  const structuredProjectData =
    extraData?.structured && typeof extraData.structured === 'object' ? extraData.structured : {};
  const projectLots = Array.isArray(extraData.lots) ? extraData.lots.filter(Boolean) : [];
  const projectDocuments = getProjectDocuments(opportunity);
  const isProject = opportunity?.type_opportunite === 'PROJET';

  return {
    title: opportunity?.titre || 'Untitled opportunity',
    isProject,
    typeLabel: getOpportunityTypeLabel(opportunity?.type_opportunite),
    statusLabel: getOpportunityStatusLabel(opportunity?.statut),
    statusBadgeVariant: opportunity?.statut === 'ACTIVE' ? 'default' : 'outline',
    organizationLabel,
    locationLabel: String(opportunity?.ville || '').trim(),
    publishedDateLabel: formatDate(opportunity?.date_publication),
    publishedAgoLabel: formatRelativeDate(opportunity?.date_publication || opportunity?.date_creation),
    deadlineDateLabel: opportunity?.date_limite ? formatDate(opportunity.date_limite) : '',
    salaryLabel: String(opportunity?.salary || '').trim(),
    contractTypeLabel: String(opportunity?.contract_type || '').trim(),
    workModeLabel:
      WORK_MODE_LABELS[String(opportunity?.normalized_work_mode || '').trim().toUpperCase()] ||
      String(opportunity?.availability || '').trim(),
    experienceLabel: formatExperienceLabel(opportunity),
    languagePreview: getLanguagePreview(opportunity, 2),
    skillsPreview: (opportunity?.skills || []).filter(Boolean).slice(0, 6),
    sourceLabel: String(opportunity?.source?.nom || '').trim(),
    companyLogo: getCompanyLogoAsset(opportunity),
    descriptionPreview: buildDescriptionPreview(opportunity),
    aiHint: getCardAiHint(opportunity, isUserAuthenticated),
    projectRegionLabel: String(extraData.region_execution || extraData.region || opportunity?.ville || '').trim(),
    projectProcedureLabel: String(structuredProjectData.procedure || extraData.procedure || '').trim(),
    projectFinancementLabel: String(structuredProjectData.financement || extraData.financement || '').trim(),
    projectTypeCommandeLabel: String(structuredProjectData.type_commande || extraData.type_commande || '').trim(),
    projectCautionLabel: String(
      extraData.caution ||
        projectLots.find((lot) => String(lot?.caution || '').trim())?.caution ||
        '',
    ).trim(),
    projectLotsCount: projectLots.length,
    projectDocumentsCount: projectDocuments.length,
    tenderRecommendation: opportunity?.tender_recommendation || null,
  };
};

export const buildSimilarOpportunityCardViewModel = (opportunity) => {
  const similarity = formatSimilarityScore(opportunity?.similarity_score);
  const companyName = formatOrganizationLabel(opportunity) || 'BidWise recommendation';

  return {
    id: opportunity?.id ?? null,
    title: opportunity?.titre || 'Untitled opportunity',
    companyName,
    similarity,
  };
};
