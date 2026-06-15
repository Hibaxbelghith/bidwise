export type StepKey =
  | 'opportunity_intent'
  | 'location'
  | 'skills'
  | 'sectors_interests'
  | 'salary'
  | 'employment_type'
  | 'target_roles'
  | 'visibility';

export type StepDefinition = {
  key: StepKey;
  title: string;
  description: string;
};

export type OnboardingData = {
  opportunity_types: string[];
  preferred_locations: string[];
  work_mode_preferences: string[];
  compensation_expectation: string;
  compensation_min_expectation: string;
  compensation_max_expectation: string;
  compensation_currency: string;
  compensation_period: string;
  employment_types: string[];
  target_roles: string[];
  competences: string[];
  domaines_interet: string[];
  profile_visibility: boolean;
};

export type OnboardingThemeColors = {
  tint: string;
  border: string;
  text: string;
  muted: string;
  card: string;
};
