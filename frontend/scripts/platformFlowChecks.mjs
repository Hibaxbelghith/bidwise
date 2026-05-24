import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { OPPORTUNITY_TYPE_OPTIONS } from '../src/features/profile/profilePreferences.js';
import { TYPE_OPTIONS } from '../src/features/opportunities/constants/opportunityOptions.js';
import {
  ORGANIZATION_CONVERSION_CONFIRMATION_FIELD,
  buildOrganizationProfilePayload,
  requiresOrganizationAccountConversion,
} from '../src/features/organization/organizationFlow.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

assert.deepEqual(
  OPPORTUNITY_TYPE_OPTIONS.map((option) => option.value),
  ['JOB', 'INTERNSHIP'],
);
assert.deepEqual(
  TYPE_OPTIONS.map((option) => option.value),
  ['EMPLOI', 'STAGE'],
);

assert.equal(requiresOrganizationAccountConversion({ account_type: 'candidate' }), true);
assert.equal(requiresOrganizationAccountConversion({ account_type: 'organization' }), false);
assert.equal(
  buildOrganizationProfilePayload({
    organization_name: ' Acme ',
    first_name: 'Lina',
    last_name: 'Mansour',
    website: 'https://example.com',
    phone: '+216 12345678',
    organization_type: 'company',
    confirm_account_conversion: true,
  })[ORGANIZATION_CONVERSION_CONFIRMATION_FIELD],
  true,
);

const opportunitiesPageSource = readFileSync(
  resolve(root, 'src/features/opportunities/pages/OpportunitiesPage.jsx'),
  'utf8',
);
assert.match(opportunitiesPageSource, /forYouLoading/);
assert.match(opportunitiesPageSource, /loading=\{hasActiveFilters \? loading \|\| forYouLoading : forYouLoading\}/);

const recommendationsHookSource = readFileSync(
  resolve(root, 'src/features/opportunities/hooks/useOpportunityRecommendations.js'),
  'utf8',
);
assert.match(recommendationsHookSource, /hasResolvedInitialLoad/);

const apiSource = readFileSync(resolve(root, 'src/lib/api.js'), 'utf8');
assert.match(apiSource, /dispatchAuthRedirect/);

const organizationCreateSource = readFileSync(
  resolve(root, 'src/features/organization/pages/CreateOrganizationAccountPage.jsx'),
  'utf8',
);
assert.match(organizationCreateSource, /confirm_account_conversion/);

const organizationRouteSource = readFileSync(
  resolve(root, 'src/features/organization/OrganizationRoute.jsx'),
  'utf8',
);
assert.match(organizationRouteSource, /ORGANIZATION_LOGIN_PATH/);
assert.match(organizationRouteSource, /requireOrganizationAccount/);

console.log('Platform flow validation checks passed');
