import axios from 'axios';

import {
  getAdminAccessToken,
  getAdminRefreshToken,
  removeAdminTokens,
  saveAdminTokens,
} from '../features/admin/adminTokenManager.js';

const API_BASE_URL = import.meta.env.VITE_API_URL;

const adminApi = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  headers: {
    'Content-Type': 'application/json',
  },
});

const redirectToAdminLogin = () => {
  if (
    window.location.pathname.startsWith('/admin') &&
    window.location.pathname !== '/admin/login'
  ) {
    window.location.replace('/admin/login');
  }
};

let isRefreshing = false;
let failedQueue = [];

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

const isAdminAuthEndpoint = (url = '') =>
  url.includes('/auth/refresh/') || url.includes('/admin/login/');

const refreshAdminAccessToken = async () => {
  const refreshToken = getAdminRefreshToken();

  if (!refreshToken) {
    throw new Error('No admin refresh token available');
  }

  const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
    refresh: refreshToken,
  });
  const newAccessToken = data.access;
  saveAdminTokens(newAccessToken, data.refresh || refreshToken);
  return newAccessToken;
};

adminApi.interceptors.request.use(
  async (config) => {
    let token = getAdminAccessToken();
    const shouldAttachAuth = !isAdminAuthEndpoint(config.url || '');

    if (shouldAttachAuth && !token && getAdminRefreshToken()) {
      if (isRefreshing) {
        token = await new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        });
      } else {
        isRefreshing = true;
        try {
          token = await refreshAdminAccessToken();
          processQueue(null, token);
        } catch (refreshError) {
          processQueue(refreshError, null);
          removeAdminTokens();
          throw refreshError;
        } finally {
          isRefreshing = false;
        }
      }
    }

    if (shouldAttachAuth && token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

adminApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !isAdminAuthEndpoint(originalRequest.url || '')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return adminApi(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getAdminRefreshToken();
      if (!refreshToken) {
        processQueue(error, null);
        removeAdminTokens();
        isRefreshing = false;
        redirectToAdminLogin();
        return Promise.reject(error);
      }

      try {
        const newAccessToken = await refreshAdminAccessToken();
        processQueue(null, newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return adminApi(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        removeAdminTokens();
        redirectToAdminLogin();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (
      error.response?.status === 403 &&
      !originalRequest?.url?.includes('/admin/login/')
    ) {
      removeAdminTokens();
      redirectToAdminLogin();
    }

    return Promise.reject(error);
  }
);

export default adminApi;
