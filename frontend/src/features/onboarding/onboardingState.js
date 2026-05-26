import { normalizeProfilePreferenceData } from '../profile/profilePreferences.js';
import {
  DEFAULT_COMPENSATION_PERIOD,
  validateSalaryRange,
} from '../profile/profileValidation.js';

export const ONBOARDING_TOTAL_STEPS = 8;
export const ONBOARDING_STORAGE_KEY = 'bidwise_onboarding';
export const USER_PROFILE_STORAGE_KEY = 'bidwise_user_profile';

export const ONBOARDING_INITIAL_DATA = {
  opportunity_types: [],
  preferred_locations: [],
  work_mode_preferences: [],
  compensation_expectation: null,
  compensation_min_expectation: null,
  compensation_max_expectation: null,
  compensation_currency: 'TND',
  compensation_period: DEFAULT_COMPENSATION_PERIOD,
  employment_types: [],
  target_roles: [],
  competences: [],
  domaines_interet: [],
  profile_visibility: true,
};

const clampStep = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.min(Math.trunc(parsed), ONBOARDING_TOTAL_STEPS - 1));
};

const normalizeStepData = (data = {}) => ({
  ...ONBOARDING_INITIAL_DATA,
  ...normalizeProfilePreferenceData(data),
});

const pickList = (primary, fallback) => (Array.isArray(primary) && primary.length ? primary : fallback);

const buildProfilePreferenceSnapshot = (profile = {}) =>
  normalizeStepData({
    opportunity_types: profile?.opportunity_types,
    preferred_locations: profile?.preferred_locations,
    work_mode_preferences: profile?.work_mode_preferences,
    compensation_expectation: profile?.compensation_expectation,
    compensation_min_expectation: profile?.compensation_min_expectation,
    compensation_max_expectation: profile?.compensation_max_expectation,
    compensation_currency: profile?.compensation_currency,
    compensation_period: profile?.compensation_period,
    employment_types: profile?.employment_types,
    target_roles: profile?.target_roles,
    competences: profile?.competences,
    domaines_interet: profile?.domaines_interet,
    profile_visibility: profile?.profile_visibility,
  });

export const buildStoredProfileData = (data, onboardingCompleted = false) => ({
  ...normalizeStepData(data),
  onboarding_completed: Boolean(onboardingCompleted),
});

export const buildOnboardingInitialData = ({
  profile,
  storedProfile,
  sessionData,
} = {}) => {
  if (sessionData) {
    return normalizeStepData(sessionData);
  }

  const profileSnapshot = buildProfilePreferenceSnapshot(profile);
  const storedSnapshot = normalizeStepData(storedProfile || {});

  return {
    ...ONBOARDING_INITIAL_DATA,
    opportunity_types: pickList(profileSnapshot.opportunity_types, storedSnapshot.opportunity_types),
    preferred_locations: pickList(profileSnapshot.preferred_locations, storedSnapshot.preferred_locations),
    work_mode_preferences: pickList(profileSnapshot.work_mode_preferences, storedSnapshot.work_mode_preferences),
    compensation_expectation:
      profile?.compensation_expectation ?? storedSnapshot.compensation_expectation ?? null,
    compensation_min_expectation:
      profile?.compensation_min_expectation ?? storedSnapshot.compensation_min_expectation ?? null,
    compensation_max_expectation:
      profile?.compensation_max_expectation ?? storedSnapshot.compensation_max_expectation ?? null,
    compensation_currency:
      profile?.compensation_currency || storedSnapshot.compensation_currency || 'TND',
    compensation_period:
      profile?.compensation_period || storedSnapshot.compensation_period || DEFAULT_COMPENSATION_PERIOD,
    employment_types: pickList(profileSnapshot.employment_types, storedSnapshot.employment_types),
    target_roles: pickList(profileSnapshot.target_roles, storedSnapshot.target_roles),
    competences: pickList(profileSnapshot.competences, storedSnapshot.competences),
    domaines_interet: pickList(profileSnapshot.domaines_interet, storedSnapshot.domaines_interet),
    profile_visibility:
      profile?.profile_visibility ?? storedSnapshot.profile_visibility ?? true,
  };
};

export const getOnboardingStepError = (step, data) => {
  const normalized = normalizeStepData(data);

  if (step === 0 && normalized.opportunity_types.length === 0) {
    return 'Select at least one option.';
  }

  if (step === 1 && normalized.work_mode_preferences.length === 0) {
    return 'Select at least one option.';
  }

  if (
    step === 1 &&
    normalized.work_mode_preferences.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID') &&
    normalized.preferred_locations.length === 0
  ) {
    return 'Choose at least one location for on-site or hybrid work.';
  }

  if (step === 2) {
    if (!normalized.competences.length) {
      return 'Add at least one skill.';
    }
  }

  if (step === 3 && normalized.domaines_interet.length === 0) {
    return 'Choose at least one sector.';
  }

  if (step === 4) {
    const salaryValidation = validateSalaryRange(
      normalized.compensation_min_expectation,
      normalized.compensation_max_expectation,
      normalized.compensation_period || DEFAULT_COMPENSATION_PERIOD,
    );
    return salaryValidation.error || '';
  }

  if (step === 6 && normalized.target_roles.length === 0) {
    return 'Add at least one target role.';
  }

  return '';
};

export const findFirstIncompleteOnboardingStep = (data) => {
  for (let step = 0; step < ONBOARDING_TOTAL_STEPS; step += 1) {
    if (getOnboardingStepError(step, data)) {
      return step;
    }
  }
  return ONBOARDING_TOTAL_STEPS - 1;
};

export const resolveOnboardingStep = ({ savedStep, profile, data } = {}) => {
  if (savedStep != null) {
    return clampStep(savedStep);
  }

  const profileStep = profile?.onboarding_completed ? null : profile?.last_onboarding_step;
  if (profileStep != null) {
    return clampStep(profileStep);
  }

  return clampStep(findFirstIncompleteOnboardingStep(data));
};

export const buildCompletedOnboardingPayload = (data, currentStep) => ({
  ...normalizeStepData(data),
  onboarding_completed: true,
  last_onboarding_step: clampStep(currentStep),
});

export const buildDeferredOnboardingPayload = (data, currentStep) => ({
  ...normalizeStepData(data),
  onboarding_completed: false,
  last_onboarding_step: clampStep(currentStep),
});
