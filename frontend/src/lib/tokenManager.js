/**
 * Gestionnaire de tokens JWT
 * Centralise toute la logique de sauvegarde/récupération/suppression des tokens
 */

const ACCESS_TOKEN_KEY = 'bidwise_access_token';
const REFRESH_TOKEN_KEY = 'bidwise_refresh_token';

let accessTokenMemory = null;

const getSessionStorage = () => {
  try {
    return window.sessionStorage;
  } catch (error) {
    console.error('Erreur lors de l\'accès à sessionStorage:', error);
    return null;
  }
};

const getLocalStorage = () => {
  try {
    return window.localStorage;
  } catch (error) {
    console.error('Erreur lors de l\'accès à localStorage:', error);
    return null;
  }
};

const cleanupLegacyAccessToken = () => {
  const localStorageRef = getLocalStorage();
  if (!localStorageRef) return;

  try {
    localStorageRef.removeItem(ACCESS_TOKEN_KEY);
  } catch (error) {
    console.error('Erreur lors du nettoyage de l\'ancien access token:', error);
  }
};

const migrateLegacyRefreshToken = () => {
  const sessionStorageRef = getSessionStorage();
  const localStorageRef = getLocalStorage();

  if (!sessionStorageRef || !localStorageRef) return null;

  try {
    const existingSessionToken = sessionStorageRef.getItem(REFRESH_TOKEN_KEY);
    if (existingSessionToken) {
      localStorageRef.removeItem(REFRESH_TOKEN_KEY);
      return existingSessionToken;
    }

    const legacyRefreshToken = localStorageRef.getItem(REFRESH_TOKEN_KEY);
    if (!legacyRefreshToken) return null;

    sessionStorageRef.setItem(REFRESH_TOKEN_KEY, legacyRefreshToken);
    localStorageRef.removeItem(REFRESH_TOKEN_KEY);
    return legacyRefreshToken;
  } catch (error) {
    console.error('Erreur lors de la migration du refresh token:', error);
    return null;
  }
};

cleanupLegacyAccessToken();
migrateLegacyRefreshToken();

/**
 * Sauvegarder les tokens
 * - access token: mémoire uniquement
 * - refresh token: sessionStorage
 * @param {string} accessToken - Token d'accès JWT
 * @param {string} refreshToken - Token de rafraîchissement
 */
export const saveTokens = (accessToken, refreshToken) => {
  accessTokenMemory = accessToken || null;

  cleanupLegacyAccessToken();

  try {
    const sessionStorageRef = getSessionStorage();
    if (!sessionStorageRef) return;

    if (refreshToken) {
      sessionStorageRef.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  } catch (error) {
    console.error('Erreur lors de la sauvegarde des tokens:', error);
  }
};

/**
 * Récupérer le token d'accès
 * @returns {string|null} Token d'accès ou null si non existant
 */
export const getAccessToken = () => accessTokenMemory;

/**
 * Récupérer le token de rafraîchissement
 * @returns {string|null} Token de rafraîchissement ou null si non existant
 */
export const getRefreshToken = () => {
  try {
    const sessionStorageRef = getSessionStorage();
    if (sessionStorageRef) {
      const refreshToken = sessionStorageRef.getItem(REFRESH_TOKEN_KEY);
      if (refreshToken) {
        return refreshToken;
      }
    }

    return migrateLegacyRefreshToken();
  } catch (error) {
    console.error('Erreur lors de la récupération du refresh token:', error);
    return null;
  }
};

/**
 * Supprimer tous les tokens (logout)
 */
export const removeTokens = () => {
  accessTokenMemory = null;

  try {
    const sessionStorageRef = getSessionStorage();
    if (sessionStorageRef) {
      sessionStorageRef.removeItem(REFRESH_TOKEN_KEY);
    }

    const localStorageRef = getLocalStorage();
    if (localStorageRef) {
      localStorageRef.removeItem(ACCESS_TOKEN_KEY);
      localStorageRef.removeItem(REFRESH_TOKEN_KEY);
    }
  } catch (error) {
    console.error('Erreur lors de la suppression des tokens:', error);
  }
};

/**
 * Vérifier si l'utilisateur est authentifié
 * @returns {boolean} true si a non-expired access token OR a refresh token exists
 */
export const isAuthenticated = () => {
  const accessToken = getAccessToken();
  if (accessToken && !isTokenExpired(accessToken)) {
    return true;
  }

  const refreshToken = getRefreshToken();
  return !!refreshToken;
};

/**
 * Utility: Décoder un JWT et récupérer les données (sans vérifier la signature)
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
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
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

  const expirationTime = payload.exp * 1000;
  const currentTime = Date.now();

  return currentTime >= expirationTime;
};
