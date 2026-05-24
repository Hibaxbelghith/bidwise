import axios from 'axios';
import { getAccessToken, getRefreshToken, isTokenExpired, saveTokens, removeTokens } from './tokenManager.js';

const API_BASE_URL = import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  headers: {
    'Content-Type': 'application/json',
  },
});

const getLoginRedirectPath = () => (
  window.location.pathname.startsWith('/admin') ? '/admin/login' : '/login'
);

const getCookie = (name) => {
  if (typeof document === 'undefined') return '';
  const prefix = `${name}=`;
  return document.cookie
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix))
    ?.slice(prefix.length) || '';
};

const isUnsafeMethod = (method = 'get') => (
  !['get', 'head', 'options', 'trace'].includes(String(method).toLowerCase())
);

const redirectToLogin = () => {
  const loginPath = getLoginRedirectPath();
  if (window.location.pathname !== loginPath) {
    window.location.href = loginPath;
  }
};

// --- Silent token refresh state ---
let isRefreshing = false;
let failedQueue = [];
let csrfRequest = null;

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  failedQueue = [];
};

const isAuthEndpoint = (url = '') =>
  url.includes('/auth/csrf/') ||
  url.includes('/auth/refresh/') ||
  url.includes('/auth/login/') ||
  url.includes('/auth/passwordless/request/') ||
  url.includes('/auth/passwordless/verify/') ||
  url.includes('/auth/google/') ||
  url.includes('/admin/login/');

const refreshAccessToken = async () => {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
    refresh: refreshToken,
  });

  const newAccessToken = data.access;
  saveTokens(newAccessToken, data.refresh || refreshToken);
  return newAccessToken;
};

const ensureCsrfToken = async () => {
  const existing = getCookie('csrftoken');
  if (existing) return existing;
  if (!csrfRequest) {
    csrfRequest = axios
      .get(`${API_BASE_URL}/auth/csrf/`, { withCredentials: true })
      .then(() => getCookie('csrftoken'))
      .finally(() => {
        csrfRequest = null;
      });
  }
  return csrfRequest;
};

// Intercepteur Request : Ajouter le token à chaque requête
api.interceptors.request.use(
  async (config) => {
    let token = getAccessToken();
    const shouldAttachAuth = !isAuthEndpoint(config.url || '');

    if (shouldAttachAuth && (!token || isTokenExpired(token)) && getRefreshToken()) {
      if (isRefreshing) {
        token = await new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        });
      } else {
        isRefreshing = true;
        try {
          token = await refreshAccessToken();
          processQueue(null, token);
        } catch (refreshError) {
          processQueue(refreshError, null);
          removeTokens();
          throw refreshError;
        } finally {
          isRefreshing = false;
        }
      }
    }

    if (shouldAttachAuth && token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (isUnsafeMethod(config.method)) {
      const csrfToken = await ensureCsrfToken();
      if (csrfToken) {
        config.headers['X-CSRFToken'] = decodeURIComponent(csrfToken);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur Response : Silent refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const shouldRedirectOnAuthFailure = !originalRequest?.skipAuthRedirect;

    // Only attempt refresh on 401, and not for the refresh endpoint itself,
    // and not if we already retried this request.
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthEndpoint(originalRequest.url || '')
    ) {
      // If a refresh is already in flight, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();

      if (!refreshToken) {
        // No refresh token available — session is over
        isRefreshing = false;
        processQueue(error, null);
        removeTokens();
        if (shouldRedirectOnAuthFailure) {
          redirectToLogin();
        }
        return Promise.reject(error);
      }

      try {
        const newAccessToken = await refreshAccessToken();

        // Resolve all queued requests with the new token
        processQueue(null, newAccessToken);

        // Retry the original request
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed — clear everything and redirect
        processQueue(refreshError, null);
        removeTokens();
        if (shouldRedirectOnAuthFailure) {
          redirectToLogin();
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
