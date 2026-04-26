import {
  buildDescriptionPreview,
  formatDate,
  formatExperienceLabel,
  formatSimilarityScore,
  getCardAiHint,
  getCompanyLogoAsset,
  getOpportunityStatusLabel,
  getOpportunityTypeLabel,
  formatOrganizationLabel,
} from '../utils/opportunityFormatters.js';
import { getLanguagePreview } from '../utils/opportunityHelpers.js';

export const buildOpportunityBrowseCardViewModel = (opportunity, isUserAuthenticated) => {
  const organizationLabel = formatOrganizationLabel(opportunity);

  return {
    title: opportunity?.titre || 'Untitled opportunity',
    typeLabel: getOpportunityTypeLabel(opportunity?.type_opportunite),
    statusLabel: getOpportunityStatusLabel(opportunity?.statut),
    statusBadgeVariant: opportunity?.statut === 'ACTIVE' ? 'default' : 'outline',
    organizationLabel,
    locationLabel: String(opportunity?.ville || '').trim(),
    publishedDateLabel: formatDate(opportunity?.date_publication),
    deadlineDateLabel: opportunity?.date_limite ? formatDate(opportunity.date_limite) : '',
    salaryLabel: String(opportunity?.salary || '').trim(),
    experienceLabel: formatExperienceLabel(opportunity),
    languagePreview: getLanguagePreview(opportunity, 2),
    companyLogo: getCompanyLogoAsset(opportunity),
    descriptionPreview: buildDescriptionPreview(opportunity),
    aiHint: getCardAiHint(opportunity, isUserAuthenticated),
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
