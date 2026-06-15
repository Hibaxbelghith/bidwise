import AsyncStorage from '@react-native-async-storage/async-storage';

const SAVED_OPPORTUNITIES_STORAGE_KEY = 'bidwise:saved-opportunities';

type SavedListener = () => void;

const listeners = new Set<SavedListener>();

function notifyListeners() {
  listeners.forEach((listener) => listener());
}

export async function readSavedOpportunityIds(): Promise<number[]> {
  try {
    const raw = await AsyncStorage.getItem(SAVED_OPPORTUNITIES_STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0);
  } catch {
    return [];
  }
}

async function writeSavedIds(ids: number[]) {
  try {
    await AsyncStorage.setItem(SAVED_OPPORTUNITIES_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Ignore storage failures for now.
  }
}

export async function isOpportunitySaved(opportunityId: number): Promise<boolean> {
  const ids = await readSavedOpportunityIds();
  return ids.includes(opportunityId);
}

export async function toggleSavedOpportunity(opportunityId: number): Promise<boolean> {
  const ids = await readSavedOpportunityIds();
  const nextIds = ids.includes(opportunityId)
    ? ids.filter((value) => value !== opportunityId)
    : [...ids, opportunityId];

  await writeSavedIds(nextIds);
  notifyListeners();
  return nextIds.includes(opportunityId);
}

export function listenSavedOpportunityChanges(listener: SavedListener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
