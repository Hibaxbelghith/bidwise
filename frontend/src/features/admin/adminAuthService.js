import adminApi from '../../lib/adminApi.js';
import { removeAdminTokens, saveAdminTokens } from './adminTokenManager.js';

const getErrorMessage = (error, fallback) => (
  error.response?.data?.detail ||
  error.response?.data?.error ||
  fallback
);

export const adminLogin = async ({ email, password }) => {
  try {
    removeAdminTokens();
    const response = await adminApi.post('/admin/login/', { email, password });
    const { access, refresh } = response.data;
    saveAdminTokens(access, refresh);
    return response.data;
  } catch (error) {
    removeAdminTokens();
    throw new Error(getErrorMessage(error, 'Admin login failed.'));
  }
};

export const validateAdminSession = async () => {
  try {
    const response = await adminApi.get('/admin/test/');
    return response.data;
  } catch (error) {
    removeAdminTokens();
    throw new Error(getErrorMessage(error, 'Admin access required.'));
  }
};

export const adminLogout = () => {
  removeAdminTokens();
};
