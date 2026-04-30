const ADMIN_REFRESH_TOKEN_KEY = 'bidwise_admin_refresh_token';

let adminAccessTokenMemory = null;

const getSessionStorage = () => {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
};

export const saveAdminTokens = (accessToken, refreshToken) => {
  adminAccessTokenMemory = accessToken || null;

  const sessionStorageRef = getSessionStorage();
  if (!sessionStorageRef) return;

  if (refreshToken) {
    sessionStorageRef.setItem(ADMIN_REFRESH_TOKEN_KEY, refreshToken);
  }
};

export const getAdminAccessToken = () => adminAccessTokenMemory;

export const getAdminRefreshToken = () => {
  const sessionStorageRef = getSessionStorage();
  return sessionStorageRef?.getItem(ADMIN_REFRESH_TOKEN_KEY) || null;
};

export const removeAdminTokens = () => {
  adminAccessTokenMemory = null;

  const sessionStorageRef = getSessionStorage();
  if (sessionStorageRef) {
    sessionStorageRef.removeItem(ADMIN_REFRESH_TOKEN_KEY);
  }
};

export const hasAdminSession = () => Boolean(
  adminAccessTokenMemory || getAdminRefreshToken()
);
