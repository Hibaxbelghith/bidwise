import type { OnboardingData, StepKey } from './onboardingTypes';

export const MAX_ONBOARDING_LOCATIONS = 10;

export function getOnboardingStepError({
  stepKey,
  data,
  salaryError,
}: {
  stepKey: StepKey;
  data: OnboardingData;
  salaryError?: string;
}): string {
  if (stepKey === 'opportunity_intent' && data.opportunity_types.length === 0) {
    return 'Select at least one opportunity type to help us recommend relevant matches.';
  }

  if (stepKey === 'location' && data.work_mode_preferences.length === 0) {
    return 'Select at least one work mode preference so we can tailor your recommendations.';
  }

  if (
    stepKey === 'location' &&
    data.work_mode_preferences.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID') &&
    data.preferred_locations.length === 0
  ) {
    return 'Choose at least one location for on-site or hybrid work.';
  }

  if (stepKey === 'location' && data.preferred_locations.length > MAX_ONBOARDING_LOCATIONS) {
    return `You can add up to ${MAX_ONBOARDING_LOCATIONS} locations.`;
  }

  if (stepKey === 'skills' && data.competences.length === 0) {
    return 'Add at least one skill.';
  }

  if (stepKey === 'sectors_interests' && data.domaines_interet.length === 0) {
    return 'Choose at least one sector.';
  }

  if (stepKey === 'salary' && salaryError) {
    return salaryError;
  }

  if (stepKey === 'employment_type' && data.employment_types.length === 0) {
    return 'Select at least one employment type.';
  }

  if (stepKey === 'target_roles' && data.target_roles.length === 0) {
    return 'Add at least one target role.';
  }

  return '';
}
