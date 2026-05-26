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
import {
	BUSINESS_FAMILY_OPTIONS,
	normalizeBusinessFamilyValues,
	normalizeLocations,
} from '../src/features/profile/profilePreferences.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

assert.equal(DEFAULT_COMPENSATION_PERIOD, 'MONTHLY');
assert.equal(COMPENSATION_PERIOD_OPTIONS[0].value, 'MONTHLY');

assert.match(validateSalaryExpectation(-1, 'MONTHLY').error, /negative/i);
assert.match(validateSalaryExpectation(10, 'MONTHLY').error, /too low/i);
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
assert.ok(BUSINESS_FAMILY_OPTIONS.some((option) => option.value === 'it_network_support'));
assert.ok(BUSINESS_FAMILY_OPTIONS.some((option) => option.value === 'accounting_finance_audit'));
assert.deepEqual(
	normalizeBusinessFamilyValues(['Support IT', 'FINTECH', 'frontend', 'marketing']),
	['it_network_support', 'accounting_finance_audit', 'frontend', 'marketing_communication']
);

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

const businessFamilySource = readFileSync(
	resolve(root, 'src/features/profile/components/BusinessFamilySelect.jsx'),
	'utf8'
);
assert.match(businessFamilySource, /BUSINESS_FAMILY_OPTIONS/);
assert.match(businessFamilySource, /Choose up to/);
assert.match(businessFamilySource, /optgroup/);

const profileSource = readFileSync(
	resolve(root, 'src/features/profile/ProfilePage.jsx'),
	'utf8'
);
assert.match(profileSource, /sticky bottom-4/);
assert.match(profileSource, /sm:grid-cols-2/);
assert.match(profileSource, /Expected salary range/);
assert.match(profileSource, /inputMode="numeric"/);
assert.match(profileSource, /Contract types/);
assert.doesNotMatch(profileSource, /Employment type/);
assert.match(profileSource, /BusinessFamilySelect/);
assert.match(profileSource, /Beginner \(0-1 year\)/);
assert.match(profileSource, /Intermediate \(3-5 years\)/);
assert.doesNotMatch(profileSource, /DÃ|ConfirmÃ|â€“/);
assert.match(profileSource, /label="Sectors"/);
assert.match(profileSource, /Choose at least one sector/);
assert.doesNotMatch(profileSource, /label="Secteurs"/);
assert.doesNotMatch(profileSource, /Matching readiness/);
assert.doesNotMatch(profileSource, /isReadyForMatching/);
assert.doesNotMatch(profileSource, /Profile ready for matching/);
assert.doesNotMatch(profileSource, /onboarding_completed: isReadyForMatching/);
assert.doesNotMatch(profileSource, /Opportunity types/);
assert.doesNotMatch(profileSource, /handleOpportunityTypeChange/);
assert.doesNotMatch(profileSource, /opportunity_types: opportunityTypesPayload/);
assert.match(profileSource, /Sign-in email/);
assert.match(profileSource, /Unique account ID/);
assert.match(profileSource, /Resume & CV/);
assert.match(profileSource, /profileCompletion/);

console.log('Profile UX validation checks passed');
