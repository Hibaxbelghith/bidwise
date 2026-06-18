import {
  DEFAULT_COMPENSATION_PERIOD,
} from './profileValidation.js';
import {
  ALL_EMPLOYMENT_TYPE_OPTIONS,
  OPPORTUNITY_TYPE_OPTIONS,
  WORK_MODE_OPTIONS,
  normalizeBusinessFamilyValues,
  normalizeLocations,
  normalizeOptionValues,
  normalizeProfilePreferenceData,
  normalizeTextList,
} from './profilePreferences.js';

export const buildProfileEditorState = ({
  user,
  profile,
  storedProfile,
} = {}) => {
  const onboarding = storedProfile || {};
  const backendSkills = normalizeTextList(profile?.competences);
  const backendInterests = normalizeBusinessFamilyValues(profile?.domaines_interet);
  const backendTargetRoles = normalizeTextList(profile?.target_roles);
  const onboardingTargetRoles = Array.isArray(onboarding?.target_roles)
    ? onboarding.target_roles.filter(Boolean)
    : [];
  const onboardingPreferences = normalizeProfilePreferenceData(onboarding);

  const backendOpportunityTypes = normalizeOptionValues(
    profile?.opportunity_types,
    OPPORTUNITY_TYPE_OPTIONS,
  );
  const backendLocations = normalizeLocations(profile?.preferred_locations);
  const backendWorkModes = normalizeOptionValues(
    profile?.work_mode_preferences,
    WORK_MODE_OPTIONS,
  );
  const backendEmploymentTypes = normalizeOptionValues(
    profile?.employment_types,
    ALL_EMPLOYMENT_TYPE_OPTIONS,
  );

  return {
    formData: {
      firstName: profile?.prenom || user?.first_name || '',
      lastName: profile?.nom || user?.last_name || '',
      experienceLevel: profile?.niveau_experience || '',
      yearsOfExperience: profile?.annees_experience?.toString() || '',
      salaryExpectation:
        profile?.compensation_expectation?.toString()
        || onboarding?.compensation_expectation?.toString()
        || '',
      salaryMinExpectation:
        profile?.compensation_min_expectation?.toString()
        || onboarding?.compensation_min_expectation?.toString()
        || '',
      salaryMaxExpectation:
        profile?.compensation_max_expectation?.toString()
        || onboarding?.compensation_max_expectation?.toString()
        || '',
      salaryPeriod:
        profile?.compensation_period
        || onboarding?.compensation_period
        || DEFAULT_COMPENSATION_PERIOD,
    },
    skills: backendSkills,
    interests: backendInterests.length
      ? backendInterests
      : onboardingPreferences.domaines_interet,
    targetRoles: backendTargetRoles.length ? backendTargetRoles : onboardingTargetRoles,
    opportunityTypes: backendOpportunityTypes.length
      ? backendOpportunityTypes
      : onboardingPreferences.opportunity_types,
    preferredLocations: backendLocations.length
      ? backendLocations
      : onboardingPreferences.preferred_locations,
    workModePreferences: backendWorkModes.length
      ? backendWorkModes
      : onboardingPreferences.work_mode_preferences,
    employmentTypes: backendEmploymentTypes.length
      ? backendEmploymentTypes
      : onboardingPreferences.employment_types,
    profileVisibility:
      profile?.profile_visibility ?? onboardingPreferences.profile_visibility,
  };
};
