import axios from 'axios';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './tokenStorage';

const DEFAULT_API_PORT = '8000';

function normalizeBaseUrl(value: string): string {
  return String(value || '').trim().replace(/\/+$/, '');
}

function resolveDevHost(): string {
  const hostUri =
    Constants.expoConfig?.hostUri
    ?? (Constants as any)?.manifest2?.extra?.expoGo?.debuggerHost
    ?? (Constants as any)?.manifest?.debuggerHost
    ?? '';

  const expoHost = String(hostUri).split(':')[0].trim();
  if (expoHost && expoHost !== 'localhost' && expoHost !== '127.0.0.1') {
    return expoHost;
  }

  if (Platform.OS === 'web') {
    const browserHost = String((globalThis as { location?: { hostname?: string } }).location?.hostname || '').trim();
    if (browserHost) {
      return browserHost;
    }
  }

  if (Platform.OS === 'android') {
    // Android emulator reaches host machine through 10.0.2.2.
    return '10.0.2.2';
  }

  return '127.0.0.1';
}

function resolveApiBaseUrl(): string {
  const explicitBaseUrl = (process.env as Record<string, string | undefined>).EXPO_PUBLIC_API_BASE_URL;
  if (explicitBaseUrl && explicitBaseUrl.trim()) {
    return normalizeBaseUrl(explicitBaseUrl);
  }

  return `http://${resolveDevHost()}:${DEFAULT_API_PORT}/api`;
}

export const API_BASE_URL = resolveApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — attach JWT token
api.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) {
    const headers = (config.headers ?? {}) as any;

    if (typeof headers.set === 'function') {
      headers.set('Authorization', `Bearer ${token}`);
    } else {
      headers.Authorization = `Bearer ${token}`;
    }

    config.headers = headers;
  }
  return config;
});

// Response interceptor — handle 401 / token refresh
let isRefreshing = false;
let pendingQueue: {
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}[] = [];

function processQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token!);
  });
  pendingQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        pendingQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refresh = await getRefreshToken();
      if (!refresh) throw new Error('No refresh token');

      const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, { refresh });
      await setTokens(data.access, refresh);
      processQueue(null, data.access);

      originalRequest.headers.Authorization = `Bearer ${data.access}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      await clearTokens();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default api;
