export type ProfileTermType = 'role' | 'skill' | 'interest';

export type ProfileSuggestion = {
  id: number | string;
  type: string;
  value: string;
  label?: string;
  aliases?: string[];
};

export type ActiveResume = {
  id: number;
  file_url?: string | null;
  uploaded_at?: string;
  source_type?: string;
  is_active?: boolean;
  parsing_status?: string | null;
  parsing_error?: string | null;
  semantic_resume_status?: string | null;
  semantic_resume_confidence?: number | null;
  semantic_resume_updated_at?: string | null;
  metadata?: {
    original_filename?: string;
    content_type?: string;
    size?: number;
  };
  parsed_text_available?: boolean;
};

export type ProfileCompletion = {
  score: number;
  missing: string[];
};

export type BidWiseProfile = {
  id?: number;
  nom?: string;
  prenom?: string;
  competences?: string[];
  domaines_interet?: string[];
  niveau_experience?: string;
  annees_experience?: number | null;
  opportunity_types?: string[];
  preferred_locations?: string[];
  preferred_location?: string | null;
  remote_preference?: string | null;
  work_mode_preferences?: string[];
  compensation_expectation?: number | null;
  compensation_min_expectation?: number | null;
  compensation_max_expectation?: number | null;
  compensation_currency?: string | null;
  compensation_period?: string | null;
  employment_types?: string[];
  target_roles?: string[];
  profile_visibility?: boolean;
  onboarding_completed?: boolean;
  last_onboarding_step?: number | null;
  active_resume?: ActiveResume | null;
  profile_completion?: ProfileCompletion;
};

export type OnboardingState = Pick<
  BidWiseProfile,
  | 'opportunity_types'
  | 'preferred_locations'
  | 'work_mode_preferences'
  | 'compensation_expectation'
  | 'compensation_min_expectation'
  | 'compensation_max_expectation'
  | 'compensation_currency'
  | 'compensation_period'
  | 'employment_types'
  | 'target_roles'
  | 'competences'
  | 'domaines_interet'
  | 'profile_visibility'
  | 'onboarding_completed'
  | 'last_onboarding_step'
>;

export type ProfileUser = {
  email?: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  profil?: BidWiseProfile;
  [key: string]: unknown;
};

export type UserProfile = ProfileUser & {
  profil?: BidWiseProfile;
};

export type ProfileEditFormState = {
  firstName: string;
  lastName: string;
  experienceLevel: string;
  yearsOfExperience: string;
  salaryMinExpectation: string;
  salaryMaxExpectation: string;
  salaryPeriod: string;
};

export type ProfileEditorState = {
  formData: ProfileEditFormState;
  opportunityTypes: string[];
  preferredLocations: string[];
  workModePreferences: string[];
  employmentTypes: string[];
  targetRoles: string[];
  skills: string[];
  interests: string[];
  profileVisibility: boolean;
};
