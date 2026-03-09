import api from './api';

/**
 * Request a one-time password for the given email.
 */
export async function requestOTP(email: string) {
  const response = await api.post('/auth/passwordless/request/', { email });
  return response.data;
}

/**
 * Verify the OTP code and receive JWT tokens.
 */
export async function verifyOTP(email: string, otp: string) {
  const response = await api.post('/auth/passwordless/verify/', { email, otp });
  return response.data as { access: string; refresh: string; is_new_user: boolean };
}

/**
 * Authenticate with a Google id_token.
 */
export async function googleLogin(id_token: string) {
  const response = await api.post('/auth/google/', { id_token });
  return response.data as { access: string; refresh: string; is_new_user: boolean };
}

/**
 * Refresh the access token.
 */
export async function refreshToken(refresh: string) {
  const response = await api.post('/auth/refresh/', { refresh });
  return response.data; // { access }
}

/**
 * Blacklist a refresh token server-side.
 */
export async function logoutServer(refresh: string) {
  await api.post('/auth/logout/', { refresh });
}

/**
 * Fetch the current user profile.
 */
export async function getProfile() {
  const response = await api.get('/profile/me/');
  return response.data;
}

/**
 * Update the current user profile (partial).
 */
export async function updateProfile(data: Record<string, unknown>) {
  const response = await api.put('/profile/me/', data);
  return response.data;
}
