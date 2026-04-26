import api from '@/src/shared/services/api';

export async function requestOTP(email: string) {
  const response = await api.post('/auth/passwordless/request/', {
    email,
    client_type: 'mobile',
  });

  return response.data;
}

export async function verifyOTP(email: string, otp: string) {
  const response = await api.post('/auth/passwordless/verify/', { email, otp });
  return response.data as { access: string; refresh: string; is_new_user: boolean };
}

export async function googleLogin(id_token: string) {
  const response = await api.post('/auth/google/', { id_token });
  return response.data as { access: string; refresh: string; is_new_user: boolean };
}

export async function refreshToken(refresh: string) {
  const response = await api.post('/auth/refresh/', { refresh });
  return response.data;
}

export async function logoutServer(refresh: string) {
  await api.post('/auth/logout/', { refresh });
}
