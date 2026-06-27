const STORAGE_KEY = 'bidwise:external-application-tracking:v1';
const DEFAULT_PROMPT_DELAY_MS = 2 * 1000;
const NOT_YET_DELAY_MS = 10 * 60 * 1000;
const REMIND_LATER_DELAY_MS = 24 * 60 * 60 * 1000;

const normalizeRecord = (record) => {
  if (!record || typeof record !== 'object') return null;

  const applicationId = Number(record.applicationId);
  const opportunityId = Number(record.opportunityId);
  if (!Number.isFinite(applicationId) || !Number.isFinite(opportunityId)) return null;

  return {
    applicationId,
    opportunityId,
    title: String(record.title || '').trim(),
    organizationLabel: String(record.organizationLabel || '').trim(),
    sourceUrl: String(record.sourceUrl || '').trim(),
    clickedAt: Number(record.clickedAt) || Date.now(),
    remindAfter: Number(record.remindAfter) || (Date.now() + DEFAULT_PROMPT_DELAY_MS),
  };
};

const readRecords = () => {
  if (typeof window === 'undefined') return [];

  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed.map(normalizeRecord).filter(Boolean);
  } catch {
    return [];
  }
};

const writeRecords = (records) => {
  if (typeof window === 'undefined') return;

  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(records));
};

export const getPendingExternalApplicationForOpportunity = (opportunityId) => {
  const normalizedId = Number(opportunityId);
  if (!Number.isFinite(normalizedId)) return null;

  return readRecords().find((record) => record.opportunityId === normalizedId) || null;
};

export const getNextPendingExternalApplication = () => {
  const records = readRecords();
  if (records.length === 0) return null;

  return [...records].sort(
    (left, right) => (left.remindAfter || 0) - (right.remindAfter || 0),
  )[0];
};

export const upsertPendingExternalApplication = (record) => {
  const normalized = normalizeRecord(record);
  if (!normalized) return null;

  const records = readRecords().filter(
    (item) => item.applicationId !== normalized.applicationId,
  );
  records.push(normalized);
  writeRecords(records);
  return normalized;
};

export const clearPendingExternalApplication = (applicationId) => {
  const normalizedId = Number(applicationId);
  if (!Number.isFinite(normalizedId)) return;

  const records = readRecords().filter((record) => record.applicationId !== normalizedId);
  writeRecords(records);
};

export const postponePendingExternalApplication = (applicationId, mode = 'not_yet') => {
  const normalizedId = Number(applicationId);
  if (!Number.isFinite(normalizedId)) return null;

  const delay = mode === 'remind_later' ? REMIND_LATER_DELAY_MS : NOT_YET_DELAY_MS;
  let nextRecord = null;

  const records = readRecords().map((record) => {
    if (record.applicationId !== normalizedId) return record;

    nextRecord = {
      ...record,
      remindAfter: Date.now() + delay,
    };
    return nextRecord;
  });

  writeRecords(records);
  return nextRecord;
};
