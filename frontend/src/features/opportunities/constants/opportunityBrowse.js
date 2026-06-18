export const SEARCH_DEBOUNCE_MS = 400;
export const DEFAULT_PAGE_SIZE = 20;
export const FETCHING_SKELETON_DELAY_MS = 1000;
export const FETCHING_SKELETON_MIN_VISIBLE_MS = 500;
export const FILTERS_STORAGE_KEY = 'opportunities:browse-state:v4';
export const RESULTS_CACHE_STORAGE_KEY = 'opportunities:browse-results-cache:v1';
export const RESULTS_CACHE_TTL_MS = 5 * 60 * 1000;
export const DEFAULT_SORT = 'quality';

export const DEFAULT_BROWSE_STATE = {
  searchInput: '',
  typeFilter: '',
  statusFilter: '',
  cityFilter: '',
  sourceFilter: '',
  workModeFilter: '',
  experienceFilter: '',
  datePostedFilter: '',
  page: 1,
};
