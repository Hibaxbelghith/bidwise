import axios from 'axios';
import { getAccessToken, removeTokens } from '../utils/tokenManager.js';

const API_BASE_URL = import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur Request : Ajouter le token à chaque requête
api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur Response : Gérer l'expiration de token (401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expiré ou invalide
      console.warn('⚠️ Token expiré ou invalide. Déconnexion automatique...');
      removeTokens();
      
      // Rediriger vers login seulement si pas déjà sur une page publique
      if (window.location.pathname !== '/login' && 
          window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;