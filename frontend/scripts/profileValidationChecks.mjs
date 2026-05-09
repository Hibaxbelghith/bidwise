import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import assert from 'node:assert/strict';

import {
	COMPENSATION_PERIOD_OPTIONS,
	DEFAULT_COMPENSATION_PERIOD,
	PROFILE_AUTOCOMPLETE_DEBOUNCE_MS,
	canonicalizeInterestLabel,
	canonicalizeSkillLabel,
	isInterestTermRejected,
	isRoleTermRejected,
	validateSalaryExpectation,
} from '../src/features/profile/profileValidation.js';
import { normalizeLocations } from '../src/features/profile/profilePreferences.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

assert.equal(DEFAULT_COMPENSATION_PERIOD, 'MONTHLY');
assert.equal(COMPENSATION_PERIOD_OPTIONS[0].value, 'MONTHLY');

const salaryInputSource = readFileSync(
	resolve(root, 'src/features/profile/components/SalaryExpectationInput.jsx'),
	'utf8'
);
assert.match(salaryInputSource, /Expected salary \(TND \/ month\)/);
assert.match(salaryInputSource, /inputMode="numeric"/);

assert.match(validateSalaryExpectation(-1, 'MONTHLY').error, /negative/i);
assert.match(validateSalaryExpectation(10, 'MONTHLY').error, /at least/i);
assert.match(validateSalaryExpectation(999999, 'MONTHLY').error, /or less/i);

assert.equal(isRoleTermRejected('React'), true);
assert.equal(isRoleTermRejected('CSS'), true);
assert.equal(isRoleTermRejected('Front'), true);
assert.equal(isRoleTermRejected('Remote'), true);

assert.equal(canonicalizeSkillLabel('css'), 'CSS');
assert.equal(canonicalizeSkillLabel('js'), 'JavaScript');
assert.equal(canonicalizeSkillLabel('py'), 'Python');

assert.equal(canonicalizeInterestLabel('sante'), 'HEALTHCARE');
assert.equal(canonicalizeInterestLabel('e-commerce'), 'ECOMMERCE');
assert.equal(isInterestTermRejected('React'), true);
assert.equal(isInterestTermRejected('Backend Developer'), true);

assert.deepEqual(
	normalizeLocations([' Tunis ', 'Tunis', '  Sfax   Centre  ', 'sfax centre']),
	['Tunis', 'Sfax Centre']
);

assert.equal(PROFILE_AUTOCOMPLETE_DEBOUNCE_MS, 250);
const autocompleteSource = readFileSync(
	resolve(root, 'src/features/profile/components/ProfileAutocompleteInput.jsx'),
	'utf8'
);
assert.match(autocompleteSource, /PROFILE_AUTOCOMPLETE_DEBOUNCE_MS/);
assert.match(autocompleteSource, /AbortController/);
assert.match(autocompleteSource, /interests\/suggest/);

const profileSource = readFileSync(
	resolve(root, 'src/features/profile/ProfilePage.jsx'),
	'utf8'
);
assert.match(profileSource, /sticky bottom-0/);
assert.match(profileSource, /sm:grid-cols-2/);
assert.match(profileSource, /ProfileSection/);
assert.match(profileSource, /Resume \/ CV/);
assert.match(profileSource, /profileCompletion/);

console.log('Profile UX validation checks passed');
