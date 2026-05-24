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
  getOnboardingStepError(4, { target_roles: [] }),
  'Select at least one option.',
);
assert.equal(
  findFirstIncompleteOnboardingStep({
    opportunity_types: ['JOB'],
    work_mode_preferences: ['REMOTE'],
    target_roles: [],
  }),
  4,
);

const deferredPayload = buildDeferredOnboardingPayload(
  {
    opportunity_types: ['JOB'],
    work_mode_preferences: ['REMOTE'],
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
    target_roles: ['Backend Developer'],
  },
  5,
);
assert.equal(completedPayload.onboarding_completed, true);
assert.equal(completedPayload.last_onboarding_step, 5);

const initialFromProfile = buildOnboardingInitialData({
  profile: {
    opportunity_types: ['JOB'],
    work_mode_preferences: ['HYBRID'],
    target_roles: ['Frontend Developer'],
  },
  storedProfile: {
    opportunity_types: ['INTERNSHIP'],
    work_mode_preferences: ['REMOTE'],
    target_roles: ['Data Engineer'],
  },
});
assert.deepEqual(initialFromProfile.opportunity_types, ['JOB']);
assert.deepEqual(initialFromProfile.work_mode_preferences, ['HYBRID']);
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
  },
});
assert.equal(editorState.formData.firstName, 'Lina');
assert.deepEqual(editorState.skills, ['Python']);
assert.deepEqual(editorState.interests, []);
assert.deepEqual(editorState.targetRoles, ['Backend Developer']);
assert.deepEqual(editorState.opportunityTypes, ['JOB']);
assert.deepEqual(editorState.workModePreferences, ['REMOTE']);

const onboardingSource = readFileSync(
  resolve(root, 'src/features/onboarding/OnboardingPage.jsx'),
  'utf8',
);
assert.match(onboardingSource, /buildDeferredOnboardingPayload/);
assert.match(onboardingSource, /Finish later/);

const profileSource = readFileSync(
  resolve(root, 'src/features/profile/ProfilePage.jsx'),
  'utf8',
);
assert.match(profileSource, /draftDirtyRef/);
assert.match(profileSource, /buildProfileEditorState/);
assert.match(profileSource, /Resume uploads refresh the authenticated user/);

console.log('Candidate flow validation checks passed');
