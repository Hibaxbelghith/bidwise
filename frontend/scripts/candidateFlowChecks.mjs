import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildCompletedOnboardingPayload,
  buildDeferredOnboardingPayload,
  buildOnboardingInitialData,
  findFirstIncompleteOnboardingStep,
  getOnboardingStepError,
} from '../src/features/onboarding/onboardingState.js';
import { buildProfileEditorState } from '../src/features/profile/profileEditorState.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

assert.equal(
  getOnboardingStepError(0, { opportunity_types: [] }),
  'Select at least one option.',
);
assert.equal(
  getOnboardingStepError(1, { work_mode_preferences: [] }),
  'Select at least one option.',
);
assert.equal(
  getOnboardingStepError(2, { competences: [] }),
  'Add at least one skill.',
);
assert.equal(
  getOnboardingStepError(3, { domaines_interet: [] }),
  'Choose at least one sector.',
);
assert.equal(
  getOnboardingStepError(6, { target_roles: [] }),
  'Add at least one target role.',
);
assert.equal(
  findFirstIncompleteOnboardingStep({
    opportunity_types: ['JOB'],
    work_mode_preferences: ['REMOTE'],
    competences: ['Python'],
    domaines_interet: [],
    target_roles: [],
  }),
  3,
);

const deferredPayload = buildDeferredOnboardingPayload(
  {
    opportunity_types: ['JOB'],
    work_mode_preferences: ['REMOTE'],
    domaines_interet: ['software_web'],
    target_roles: ['Backend Developer'],
  },
  2,
);
assert.equal(deferredPayload.onboarding_completed, false);
assert.equal(deferredPayload.last_onboarding_step, 2);

const completedPayload = buildCompletedOnboardingPayload(
  {
    opportunity_types: ['JOB'],
    work_mode_preferences: ['REMOTE'],
    competences: ['Python'],
    domaines_interet: ['software_web'],
    target_roles: ['Backend Developer'],
  },
  7,
);
assert.equal(completedPayload.onboarding_completed, true);
assert.equal(completedPayload.last_onboarding_step, 7);

const initialFromProfile = buildOnboardingInitialData({
  profile: {
    opportunity_types: ['JOB'],
    work_mode_preferences: ['HYBRID'],
    domaines_interet: ['software_web'],
    target_roles: ['Frontend Developer'],
  },
  storedProfile: {
    opportunity_types: ['INTERNSHIP'],
    work_mode_preferences: ['REMOTE'],
    domaines_interet: ['data_ai'],
    target_roles: ['Data Engineer'],
  },
});
assert.deepEqual(initialFromProfile.opportunity_types, ['JOB']);
assert.deepEqual(initialFromProfile.work_mode_preferences, ['HYBRID']);
assert.deepEqual(initialFromProfile.domaines_interet, ['software_web']);
assert.deepEqual(initialFromProfile.target_roles, ['Frontend Developer']);

const editorState = buildProfileEditorState({
  user: { first_name: 'Lina', last_name: 'Mansour' },
  profile: {
    prenom: '',
    nom: '',
    competences: ['Python'],
    domaines_interet: [],
    target_roles: [],
    opportunity_types: [],
    preferred_locations: [],
    work_mode_preferences: [],
    employment_types: [],
    profile_visibility: true,
  },
  storedProfile: {
    target_roles: ['Backend Developer'],
    opportunity_types: ['JOB'],
    work_mode_preferences: ['REMOTE'],
    domaines_interet: ['software_web'],
  },
});
assert.equal(editorState.formData.firstName, 'Lina');
assert.deepEqual(editorState.skills, ['Python']);
assert.deepEqual(editorState.interests, ['software_web']);
assert.deepEqual(editorState.targetRoles, ['Backend Developer']);
assert.deepEqual(editorState.opportunityTypes, ['JOB']);
assert.deepEqual(editorState.workModePreferences, ['REMOTE']);

const onboardingSource = readFileSync(
  resolve(root, 'src/features/onboarding/OnboardingPage.jsx'),
  'utf8',
);
assert.match(onboardingSource, /StepSectors/);
assert.match(onboardingSource, /Choose at least one sector/);
assert.match(onboardingSource, /What contract types are you open to/);
assert.doesNotMatch(onboardingSource, /What type of work arrangement do you prefer/);
assert.doesNotMatch(onboardingSource, /Saving…|Ã|â/);
assert.match(onboardingSource, /Skip for now/);

const profilePreferencesSource = readFileSync(
  resolve(root, 'src/features/profile/profilePreferences.js'),
  'utf8',
);
assert.match(profilePreferencesSource, /Internships and trainee programs/);
assert.match(profilePreferencesSource, /Calls for proposals, funding, and R&D/);
assert.doesNotMatch(profilePreferencesSource, /Stage et|Appels d'offres|financements|Ã|â/);

const profileSource = readFileSync(
  resolve(root, 'src/features/profile/ProfilePage.jsx'),
  'utf8',
);
assert.match(profileSource, /buildProfileEditorState/);
assert.match(profileSource, /Sign-in email/);
assert.match(profileSource, /Unique account ID/);

console.log('Candidate flow validation checks passed');
