import { SAVED_OPPORTUNITY_IDS_KEY } from '../constants/opportunityDetail.js';

export const SAVED_OPPORTUNITIES_CHANGED_EVENT = 'bidwise:saved-opportunities-changed';

const normalizeId = (id) => String(id ?? '').trim();

export const readSavedOpportunityIds = () => {
  if (typeof window === 'undefined') return new Set();

  try {
    const raw = window.localStorage.getItem(SAVED_OPPORTUNITY_IDS_KEY);
    if (!raw) return new Set();

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();

    return new Set(parsed.map(normalizeId).filter(Boolean));
  } catch {
    return new Set();
  }
};

export const getSavedOpportunityIds = () => Array.from(readSavedOpportunityIds());

export const writeSavedOpportunityIds = (ids) => {
  if (typeof window === 'undefined') return;

  const values = Array.from(ids || []).map(normalizeId).filter(Boolean);
  window.localStorage.setItem(SAVED_OPPORTUNITY_IDS_KEY, JSON.stringify(values));
  window.dispatchEvent(
    new CustomEvent(SAVED_OPPORTUNITIES_CHANGED_EVENT, {
      detail: { ids: values },
    }),
  );
};

export const isOpportunitySaved = (id) => {
  const normalizedId = normalizeId(id);
  if (!normalizedId) return false;

  return readSavedOpportunityIds().has(normalizedId);
};

export const saveOpportunity = (id) => {
  const normalizedId = normalizeId(id);
  if (!normalizedId) return false;

  const savedIds = readSavedOpportunityIds();
  savedIds.add(normalizedId);
  writeSavedOpportunityIds(savedIds);
  return true;
};

export const removeSavedOpportunity = (id) => {
  const normalizedId = normalizeId(id);
  if (!normalizedId) return false;

  const savedIds = readSavedOpportunityIds();
  savedIds.delete(normalizedId);
  writeSavedOpportunityIds(savedIds);
  return false;
};

export const toggleSavedOpportunity = (id) => {
  const normalizedId = normalizeId(id);
  if (!normalizedId) return false;

  const savedIds = readSavedOpportunityIds();
  const nextSaved = !savedIds.has(normalizedId);

  if (nextSaved) {
    savedIds.add(normalizedId);
  } else {
    savedIds.delete(normalizedId);
  }

  writeSavedOpportunityIds(savedIds);
  return nextSaved;
};

export const listenSavedOpportunityChanges = (handler) => {
  if (typeof window === 'undefined') return () => {};

  const handleCustomEvent = (event) => {
    handler(Array.isArray(event?.detail?.ids) ? event.detail.ids : getSavedOpportunityIds());
  };

  const handleStorageEvent = (event) => {
    if (event.key === SAVED_OPPORTUNITY_IDS_KEY) {
      handler(getSavedOpportunityIds());
    }
  };

  window.addEventListener(SAVED_OPPORTUNITIES_CHANGED_EVENT, handleCustomEvent);
  window.addEventListener('storage', handleStorageEvent);

  return () => {
    window.removeEventListener(SAVED_OPPORTUNITIES_CHANGED_EVENT, handleCustomEvent);
    window.removeEventListener('storage', handleStorageEvent);
  };
};
