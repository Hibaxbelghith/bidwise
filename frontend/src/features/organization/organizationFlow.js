export const ORGANIZATION_AUTH_INTENT = 'organization';
export const ORGANIZATION_LOGIN_PATH = `/login?intent=${ORGANIZATION_AUTH_INTENT}`;
export const ORGANIZATION_CREATE_ACCOUNT_PATH = '/organization/create-account';
export const ORGANIZATION_DASHBOARD_PATH = '/organization/dashboard';

export const ORGANIZATION_TYPES = [
  { value: 'company', label: 'Company' },
  { value: 'startup', label: 'Startup' },
  { value: 'public', label: 'Public institution' },
  { value: 'ngo', label: 'NGO' },
  { value: 'other', label: 'Other' },
];

const ORGANIZATION_TYPE_VALUES = new Set(ORGANIZATION_TYPES.map((type) => type.value));
const TUNISIA_PHONE_PATTERN = /^\+216\d{8}$/;

export const normalizeWhitespace = (value) => String(value || '').trim().replace(/\s+/g, ' ');

export const normalizeTunisiaPhone = (value) => String(value || '').trim().replace(/\s+/g, '');

export const isOrganizationAccount = (user) => user?.account_type === 'organization';

export const isOrganizationProfileComplete = (profile) => {
  if (!profile) return false;

  return Boolean(
    normalizeWhitespace(profile.organization_name) &&
      normalizeWhitespace(profile.first_name) &&
      normalizeWhitespace(profile.last_name) &&
      TUNISIA_PHONE_PATTERN.test(normalizeTunisiaPhone(profile.phone)) &&
      ORGANIZATION_TYPE_VALUES.has(profile.organization_type)
  );
};

export const validateOrganizationProfileForm = (values) => {
  const errors = {};
  const organizationName = normalizeWhitespace(values.organization_name);
  const firstName = normalizeWhitespace(values.first_name);
  const lastName = normalizeWhitespace(values.last_name);
  const phone = normalizeTunisiaPhone(values.phone);
  const website = String(values.website || '').trim();

  if (!organizationName) {
    errors.organization_name = 'Enter your organization name';
  } else if (organizationName.length > 180) {
    errors.organization_name = 'Organization name is too long.';
  }

  if (!firstName) {
    errors.first_name = 'Enter your first name';
  } else if (firstName.length > 100) {
    errors.first_name = 'First name is too long.';
  }

  if (!lastName) {
    errors.last_name = 'Enter your last name';
  } else if (lastName.length > 100) {
    errors.last_name = 'Last name is too long.';
  }

  if (!phone) {
    errors.phone = 'Enter your phone number';
  } else if (!TUNISIA_PHONE_PATTERN.test(phone)) {
    errors.phone = 'Enter a valid Tunisian phone number.';
  }

  if (website) {
    try {
      const url = new URL(website);
      if (!['http:', 'https:'].includes(url.protocol)) {
        errors.website = 'Enter a valid website URL.';
      }
    } catch {
      errors.website = 'Enter a valid website URL (e.g., https://www.example.com).';
    }
  }

  if (!values.organization_type) {
    errors.organization_type = 'Select your organization type';
  } else if (!ORGANIZATION_TYPE_VALUES.has(values.organization_type)) {
    errors.organization_type = 'Select a valid organization type';
  }

  return errors;
};

export const buildOrganizationProfilePayload = (values) => ({
  organization_name: normalizeWhitespace(values.organization_name),
  first_name: normalizeWhitespace(values.first_name),
  last_name: normalizeWhitespace(values.last_name),
  website: String(values.website || '').trim(),
  phone: normalizeTunisiaPhone(values.phone),
  organization_type: values.organization_type,
});

export const getPostAuthRedirectPath = ({ user, isNewUser = false, organizationIntent = false }) => {
  if (organizationIntent || isOrganizationAccount(user)) {
    return isOrganizationProfileComplete(user?.organization_profile)
      ? ORGANIZATION_DASHBOARD_PATH
      : ORGANIZATION_CREATE_ACCOUNT_PATH;
  }

  return isNewUser || !user?.profil?.onboarding_completed ? '/onboarding' : '/opportunities';
};
