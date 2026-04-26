export const SEARCH_DEBOUNCE_MS = 400;
export const DEFAULT_PAGE_SIZE = 20;
export const FETCHING_SKELETON_DELAY_MS = 1000;
export const FETCHING_SKELETON_MIN_VISIBLE_MS = 500;
export const FILTERS_STORAGE_KEY = 'opportunities:browse-state:v1';
export const DEFAULT_ORDERING = '-date_publication';

export const DEFAULT_BROWSE_STATE = {
  searchInput: '',
  typeFilter: '',
  statusFilter: '',
  cityFilter: '',
  ordering: DEFAULT_ORDERING,
  page: 1,
};
