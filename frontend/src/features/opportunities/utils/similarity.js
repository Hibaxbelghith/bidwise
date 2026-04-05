const clampSimilarityScore = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(value, 1));
};

export const formatSimilarityScore = (rawScore) => {
  const score = clampSimilarityScore(rawScore);
  const percentage = Math.round(score * 100);
  let label = 'Related';

  if (percentage >= 80) {
    label = 'Very relevant';
  } else if (percentage >= 60) {
    label = 'Relevant';
  }

  return {
    percentage,
    label,
    raw: score.toFixed(2),
  };
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
      item.organisation_nom || item.organization || item.organisation
    );
    const compositeKey = `${title}::${organization}`;
    if (title && byComposite.has(compositeKey)) continue;
    if (title) byComposite.add(compositeKey);

    result.push(item);
  }

  return result;
};
