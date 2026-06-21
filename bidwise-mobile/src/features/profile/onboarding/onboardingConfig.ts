import {
  DEFAULT_COMPENSATION_CURRENCY,
  DEFAULT_COMPENSATION_PERIOD,
} from '@/src/features/profile/constants/profileOptions';

import type { OnboardingData, StepDefinition } from './onboardingTypes';

export const MAX_ROLES = 5;

export const STEP_DEFINITIONS: StepDefinition[] = [
  {
    key: 'opportunity_intent',
    title: 'What brings you to BidWise?',
    description: 'Select the type of opportunities you are looking for. This helps us personalize your experience.',
  },
  {
    key: 'location',
    title: 'Where would you like to work?',
    description: 'Location is required for on-site or hybrid work, and optional for remote.',
  },
  {
    key: 'tender_preferences',
    title: 'Which tenders should we prioritize?',
    description: 'Choose an official tender category so BidWise can rank public projects for you.',
  },
  {
    key: 'skills',
    title: 'Add your key skills',
    description: 'Skills power your AI match score.',
  },
  {
    key: 'sectors_interests',
    title: 'Choose your sectors',
    description: 'Select the professional domains that best describe your profile.',
  },
  {
    key: 'salary',
    title: 'Expected salary range',
    description: 'Share an optional TND/month range so matches are less brittle.',
  },
  {
    key: 'employment_type',
    title: 'What contract types are you open to?',
    description: 'Select the employment contracts you would consider.',
  },
  {
    key: 'target_roles',
    title: 'What roles are you targeting?',
    description: 'This improves our recommendation engine.',
  },
  {
    key: 'visibility',
    title: 'Profile visibility',
    description: 'Control how your profile appears to recruiters. You can change this anytime in settings.',
  },
];

export const INITIAL_ONBOARDING_DATA: OnboardingData = {
  opportunity_types: [],
  tender_preferences: { categories: [], max_budget: null },
  preferred_locations: [],
  work_mode_preferences: [],
  compensation_expectation: '',
  compensation_min_expectation: '',
  compensation_max_expectation: '',
  compensation_currency: DEFAULT_COMPENSATION_CURRENCY,
  compensation_period: DEFAULT_COMPENSATION_PERIOD,
  employment_types: [],
  target_roles: [],
  competences: [],
  domaines_interet: [],
  profile_visibility: true,
};
