const NLP_METADATA_KEY_PATTERN =
  /\b(?:type|organization|organisation|title|location)\s*:\s*/gi;
const LEADING_TYPE_VALUE_PATTERN =
  /^\s*(?:job|stage|internship|research|project|funding)\b[\s,;:|.-]*/i;

export const cleanDescription = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return 'No description available';

  const cleaned = raw
    .replace(NLP_METADATA_KEY_PATTERN, ' ')
    .replace(LEADING_TYPE_VALUE_PATTERN, '')
    .replace(/\s+/g, ' ')
    .trim();

  return cleaned || 'No description available';
};
