import { DEFAULT_COMPENSATION_CURRENCY } from '@/src/features/profile/constants/profileOptions';
import type { BidWiseProfile } from '@/src/features/profile/types';
import { normalizeProfilePreferenceData } from '@/src/features/profile/utils/profileValidation';

import { INITIAL_ONBOARDING_DATA, STEP_DEFINITIONS } from './onboardingConfig';
import type { OnboardingData } from './onboardingTypes';

function toInputString(value: unknown): string {
  if (value === null || value === undefined) return '';
  return String(value).trim();
}

function clampStep(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.min(Math.trunc(parsed), STEP_DEFINITIONS.length - 1));
}

export function buildOnboardingDataFromProfile(profile?: BidWiseProfile | null): OnboardingData {
  const normalized = normalizeProfilePreferenceData({
    opportunity_types: profile?.opportunity_types,
    tender_preferences: profile?.tender_preferences,
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

  return {
    ...INITIAL_ONBOARDING_DATA,
    ...normalized,
    compensation_expectation: toInputString(profile?.compensation_expectation),
    compensation_min_expectation: toInputString(profile?.compensation_min_expectation),
    compensation_max_expectation: toInputString(profile?.compensation_max_expectation),
    compensation_currency:
      profile?.compensation_currency || normalized.compensation_currency || DEFAULT_COMPENSATION_CURRENCY,
    compensation_period: profile?.compensation_period || normalized.compensation_period,
  };
}

export function resolveOnboardingStepFromProfile(profile?: BidWiseProfile | null): number {
  if (!profile) return 0;
  if (profile.onboarding_completed) return 0;
  return clampStep(profile.last_onboarding_step);
}
