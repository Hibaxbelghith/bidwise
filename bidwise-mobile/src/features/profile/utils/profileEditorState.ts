import type {
  BidWiseProfile,
  ProfileEditFormState,
  ProfileEditorState,
  ProfileUser,
} from '@/src/features/profile/types';
import {
  DEFAULT_COMPENSATION_PERIOD,
  normalizeBusinessFamilyValues,
  normalizeLocations,
  normalizeOptionValues,
  normalizeSkillList,
  normalizeTextList,
} from '@/src/features/profile/utils/profileValidation';
import {
  EMPLOYMENT_TYPE_OPTIONS,
  OPPORTUNITY_TYPE_OPTIONS,
  WORK_MODE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';

export const EXPERIENCE_LEVEL_OPTIONS = [
  { value: 'DEBUTANT', label: 'Beginner (0-1 year)' },
  { value: 'JUNIOR', label: 'Junior (1-3 years)' },
  { value: 'CONFIRME', label: 'Intermediate (3-5 years)' },
  { value: 'SENIOR', label: 'Senior (5+ years)' },
];

export function buildProfileEditorState(user: ProfileUser | null): ProfileEditorState {
  const profile = user?.profil;

  return {
    formData: buildProfileEditFormData(profile, user),
    opportunityTypes: normalizeOptionValues(profile?.opportunity_types, OPPORTUNITY_TYPE_OPTIONS),
    preferredLocations: normalizeLocations(profile?.preferred_locations),
    workModePreferences: normalizeOptionValues(profile?.work_mode_preferences, WORK_MODE_OPTIONS),
    employmentTypes: normalizeOptionValues(profile?.employment_types, EMPLOYMENT_TYPE_OPTIONS),
    targetRoles: normalizeTextList(profile?.target_roles),
    skills: normalizeSkillList(profile?.competences),
    interests: normalizeBusinessFamilyValues(profile?.domaines_interet),
    profileVisibility: profile?.profile_visibility ?? true,
  };
}

function buildProfileEditFormData(
  profile: BidWiseProfile | undefined,
  user: ProfileUser | null,
): ProfileEditFormState {
  return {
    firstName: String(profile?.prenom || user?.first_name || '').trim(),
    lastName: String(profile?.nom || user?.last_name || '').trim(),
    experienceLevel: String(profile?.niveau_experience || '').trim(),
    yearsOfExperience:
      profile?.annees_experience != null ? String(profile.annees_experience) : '',
    salaryMinExpectation:
      profile?.compensation_min_expectation != null
        ? String(profile.compensation_min_expectation)
        : '',
    salaryMaxExpectation:
      profile?.compensation_max_expectation != null
        ? String(profile.compensation_max_expectation)
        : '',
    salaryPeriod: String(profile?.compensation_period || DEFAULT_COMPENSATION_PERIOD).trim(),
  };
}

export function buildProfileUpdatePayload(state: ProfileEditorState) {
  return {
    prenom: state.formData.firstName.trim() || null,
    nom: state.formData.lastName.trim() || null,
    niveau_experience: state.formData.experienceLevel || null,
    opportunity_types: state.opportunityTypes,
    preferred_locations: state.preferredLocations,
    work_mode_preferences: state.workModePreferences,
    employment_types: state.employmentTypes,
    target_roles: normalizeTextList(state.targetRoles),
    competences: normalizeSkillList(state.skills),
    domaines_interet: normalizeBusinessFamilyValues(state.interests),
    profile_visibility: state.profileVisibility,
  };
}
