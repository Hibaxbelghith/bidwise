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
import { getLanguagePreview } from '../utils/opportunityHelpers.js';

const WORK_MODE_LABELS = {
  REMOTE: 'Remote',
  HYBRID: 'Hybrid',
  ON_SITE: 'On site',
};

const isBenchmarkSource = (opportunity) => {
  const sourceName = String(opportunity?.source?.nom || '').trim().toLowerCase();
  const sourceUrl = String(opportunity?.source_item_url || '').trim().toLowerCase();
  return (
    sourceName.includes('bidwise recommendation benchmark') ||
    sourceUrl.includes('benchmark.bidwise.local')
  );
};

export const buildOpportunityBrowseCardViewModel = (opportunity, isUserAuthenticated) => {
  const organizationLabel = formatOrganizationLabel(opportunity);
  const hideSource = isBenchmarkSource(opportunity);

  return {
    title: opportunity?.titre || 'Untitled opportunity',
    typeLabel: getOpportunityTypeLabel(opportunity?.type_opportunite),
    statusLabel: getOpportunityStatusLabel(opportunity?.statut),
    statusBadgeVariant: opportunity?.statut === 'ACTIVE' ? 'default' : 'outline',
    organizationLabel,
    locationLabel: String(opportunity?.ville || '').trim(),
    publishedDateLabel: formatDate(opportunity?.date_publication),
    publishedAgoLabel: formatRelativeDate(opportunity?.date_creation || opportunity?.date_publication),
    deadlineDateLabel: opportunity?.date_limite ? formatDate(opportunity.date_limite) : '',
    salaryLabel: String(opportunity?.salary || '').trim(),
    contractTypeLabel: String(opportunity?.contract_type || '').trim(),
    workModeLabel:
      WORK_MODE_LABELS[String(opportunity?.normalized_work_mode || '').trim().toUpperCase()] ||
      String(opportunity?.availability || '').trim(),
    experienceLabel: formatExperienceLabel(opportunity),
    languagePreview: getLanguagePreview(opportunity, 2),
    skillsPreview: (opportunity?.skills || []).filter(Boolean).slice(0, 6),
    sourceLabel: hideSource ? '' : String(opportunity?.source?.nom || '').trim(),
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
