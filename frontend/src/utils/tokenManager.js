/**
 * Gestionnaire de tokens JWT
 * Centralise toute la logique de sauvegarde/récupération/suppression des tokens
 */

const ACCESS_TOKEN_KEY = 'bidwise_access_token';
const REFRESH_TOKEN_KEY = 'bidwise_refresh_token';

/**
 * Sauvegarder les tokens dans localStorage
 * @param {string} accessToken - Token d'accès JWT
 * @param {string} refreshToken - Token de rafraîchissement
 */
export const saveTokens = (accessToken, refreshToken) => {
  try {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  } catch (error) {
    console.error('Erreur lors de la sauvegarde des tokens:', error);
  }
};

/**
 * Récupérer le token d'accès
 * @returns {string|null} Token d'accès ou null si non existant
 */
export const getAccessToken = () => {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch (error) {
    console.error('Erreur lors de la récupération du token:', error);
    return null;
  }
};

/**
 * Récupérer le token de rafraîchissement
 * @returns {string|null} Token de rafraîchissement ou null si non existant
 */
export const getRefreshToken = () => {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch (error) {
    console.error('Erreur lors de la récupération du refresh token:', error);
    return null;
  }
};

/**
 * Supprimer tous les tokens (logout)
 */
export const removeTokens = () => {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch (error) {
    console.error('Erreur lors de la suppression des tokens:', error);
  }
};

/**
 * Vérifier si l'utilisateur est authentifié
 * @returns {boolean} true si un token d'accès existe
 */
export const isAuthenticated = () => {
  const token = getAccessToken();
  return !!token; // Double négation pour convertir en booléen
};

/**
 * Utility: Décoder un JWT et récupérer les données (sans vérifier la signature)
 * ⚠️ À utiliser uniquement pour lire les données, pas pour vérifier l'authenticité
 * @param {string} token - JWT token
 * @returns {object|null} Payload décodé ou null
 */
export const decodeToken = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Erreur lors du décodage du token:', error);
    return null;
  }
};

/**
 * Vérifier si le token est expiré
 * @param {string} token - JWT token
 * @returns {boolean} true si expiré, false sinon
 */
export const isTokenExpired = (token) => {
  if (!token) return true;
  
  const payload = decodeToken(token);
  if (!payload || !payload.exp) return true;
  
  // exp est en secondes, Date.now() est en millisecondes
  const expirationTime = payload.exp * 1000;
  const currentTime = Date.now();
  
  return currentTime >= expirationTime;
};
