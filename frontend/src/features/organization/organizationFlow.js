export const ORGANIZATION_AUTH_INTENT = 'organization';
export const ORGANIZATION_LOGIN_PATH = `/login?intent=${ORGANIZATION_AUTH_INTENT}`;
export const ORGANIZATION_CREATE_ACCOUNT_PATH = '/organization/create-account';
export const ORGANIZATION_DASHBOARD_PATH = '/organization/dashboard';
export const ORGANIZATION_OPPORTUNITY_SUBMITTED_PATH = '/organization/post/submitted';

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

export const normalizePublicUrl = (value) => {
  const text = String(value || '').trim();
  if (!text) return '';
  if (text.startsWith('/')) return text;
  if (/^https?:\/\//i.test(text)) return text;
  return `https://${text}`;
};

const isValidPublicUrl = (value) => {
  const normalizedValue = normalizePublicUrl(value);
  if (normalizedValue.startsWith('/logos_sites_sources/') || normalizedValue.startsWith('/media/')) {
    return true;
  }

  try {
    const url = new URL(normalizedValue);
    return ['http:', 'https:'].includes(url.protocol);
  } catch {
    return false;
  }
};

export const isOrganizationAccount = (user) => user?.account_type === 'organization';

export const getCandidateProfileCompletionScore = (user) => {
  const score = Number(user?.profil?.profile_completion?.score);
  return Number.isFinite(score) ? Math.max(0, Math.min(score, 100)) : 0;
};

export const shouldStartCandidateOnboarding = (user) => {
  if (!user?.profil) return true;
  if (user.profil.onboarding_completed) return false;

  return getCandidateProfileCompletionScore(user) <= 0;
};

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
  const website = normalizePublicUrl(values.website);
  const logo = normalizePublicUrl(values.logo);

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
    if (!isValidPublicUrl(website)) {
      errors.website = 'Enter a valid website URL (e.g., https://www.example.com).';
    }
  }

  if (logo && !isValidPublicUrl(logo)) {
    errors.logo = 'Enter a valid public logo URL (e.g., https://cdn.example.com/logo.png).';
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
  website: normalizePublicUrl(values.website),
  logo: normalizePublicUrl(values.logo),
  phone: normalizeTunisiaPhone(values.phone),
  organization_type: values.organization_type,
});

export const getPostAuthRedirectPath = ({ user, isNewUser = false, organizationIntent = false }) => {
  if (organizationIntent || isOrganizationAccount(user)) {
    return isOrganizationProfileComplete(user?.organization_profile)
      ? ORGANIZATION_DASHBOARD_PATH
      : ORGANIZATION_CREATE_ACCOUNT_PATH;
  }

  return shouldStartCandidateOnboarding(user) ? '/onboarding' : '/opportunities';
};
