import { formatExperienceLabel, formatOrganizationLabel, formatProjectDocumentType } from './opportunityFormatters.js';

export const dedupeStrings = (items) => {
  const result = [];
  const seen = new Set();

  for (const value of items || []) {
    const normalized = String(value || '').trim();
    if (!normalized) continue;

    const key = normalized.toLowerCase();
    if (seen.has(key)) continue;

    seen.add(key);
    result.push(normalized);
  }

  return result;
};

export const hasDisplayValue = (value) => {
  if (Array.isArray(value)) return dedupeStrings(value).length > 0;
  if (value && typeof value === 'object') return Object.keys(value).length > 0;
  return Boolean(String(value || '').trim());
};

export const getSkills = (opportunity) => dedupeStrings(opportunity?.skills || []);

export const getLanguagePreview = (opportunity, limit = 3) => {
  const languages = dedupeStrings(opportunity?.languages || opportunity?.languages_fallback || []);
  return languages.slice(0, limit);
};

export const getProjectDocuments = (opportunity) => {
  const extraData =
    opportunity?.extra_data && typeof opportunity.extra_data === 'object' ? opportunity.extra_data : {};
  const documents = [];
  const seenUrls = new Set();

  const pushDocument = (url, type, label) => {
    const normalizedUrl = String(url || '').trim();
    if (!normalizedUrl || seenUrls.has(normalizedUrl)) return;

    documents.push({
      url: normalizedUrl,
      type: String(type || '').trim() || 'autres',
      label: String(label || '').trim() || formatProjectDocumentType(type, label),
    });
    seenUrls.add(normalizedUrl);
  };

  if (Array.isArray(extraData.documents)) {
    extraData.documents.forEach((document) => {
      if (!document || typeof document !== 'object') return;
      pushDocument(document.url, document.type, document.label);
    });
  }

  pushDocument(extraData.cahier_des_charges_url, 'cahier_des_charges', 'Cahier des charges');
  pushDocument(extraData.pdf_url, 'avis_appel_offres', "Avis d'appel d'offres");

  return documents;
};

const formatExtraDataValue = (value) => {
  if (Array.isArray(value)) {
    return dedupeStrings(value).join(', ');
  }

  if (value && typeof value === 'object') {
    return '';
  }

  return String(value || '').trim();
};

export const buildAdditionalInfoItems = (extraData) => {
  if (!extraData || typeof extraData !== 'object') return [];

  const fields = [
    ['Sector', extraData.company_sector],
    ['Company size', extraData.company_size],
    ['Reference', extraData.reference],
    ['Experience', extraData.experience_text],
    ['Contract types', extraData.contract_types],
    ['Education levels', extraData.education_levels],
    ['Qualifications', extraData.job_qualifications],
  ];

  return fields
    .map(([label, value]) => ({ label, value: formatExtraDataValue(value) }))
    .filter((item) => item.value);
};

const normalizeText = (value) => String(value || '').trim().toLowerCase();

export const dedupeSimilarOpportunities = (items) => {
  const byId = new Set();
  const byComposite = new Set();
  const result = [];

  for (const item of items || []) {
    if (!item) continue;

    const id = item.id;
    if (id != null) {
      if (byId.has(id)) continue;
      byId.add(id);
    }

    const title = normalizeText(item.titre);
    const organization = normalizeText(
      item.organisation_nom || item.organization || item.organisation,
    );
    const compositeKey = `${title}::${organization}`;
    if (title && byComposite.has(compositeKey)) continue;
    if (title) byComposite.add(compositeKey);

    result.push(item);
  }

  return result;
};

export const getSemanticMatchScore = (items) => {
  const scores = (items || [])
    .map((item) => Number(item?.similarity_score))
    .filter((value) => Number.isFinite(value));

  if (!scores.length) return null;

  return Math.round(Math.max(...scores) * 100);
};

export const buildMatchBullets = (opportunity, semanticScore) => {
  const bullets = [];
  const skills = getSkills(opportunity).slice(0, 3);
  const location = String(opportunity?.ville || '').trim();
  const experience = formatExperienceLabel(opportunity);

  if (skills.length) {
    bullets.push(`Core skills alignment around ${skills.join(', ')}.`);
  }
  if (experience) {
    bullets.push(`Experience fit: ${experience}.`);
  }
  if (location) {
    bullets.push(`Location fit includes ${location}.`);
  }
  if (semanticScore !== null) {
    bullets.push(`Current semantic match score: ${semanticScore}%.`);
  }

  if (!bullets.length) {
    bullets.push('BidWise identified a baseline relevance based on semantic similarity.');
  }

  return bullets.slice(0, 3);
};

export const buildAIDraft = (opportunity) => {
  const title = String(opportunity?.titre || 'this role').trim();
  const company = formatOrganizationLabel(opportunity);
  const skills = getSkills(opportunity).slice(0, 4);
  const skillsLine = skills.length ? ` with experience in ${skills.join(', ')}` : '';

  return `Hi ${company} team,\n\nI am interested in ${title}${skillsLine}. I can contribute quickly with a structured approach and measurable outcomes.\n\nBest regards,\nYour Name`;
};
