/**
 * AuthContext - Contexte d'authentification global
 * Fournit l'état d'authentification à toute l'application
 */

import { createContext, useContext, useState, useEffect } from 'react';
import * as authService from '../services/authService';
import { isAuthenticated as checkAuth, removeTokens, getAccessToken, isTokenExpired } from '../utils/tokenManager';

// Créer le contexte
const AuthContext = createContext(null);

/**
 * Hook personnalisé pour utiliser le contexte d'authentification
 * Utilisation: const { user, login, logout } = useAuth();
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth doit être utilisé à l\'intérieur d\'un AuthProvider');
  }
  return context;
};

/**
 * Provider du contexte d'authentification
 * Wrapper toute l'application pour rendre l'état auth disponible partout
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Charger l'utilisateur au montage si un token existe
   */
  useEffect(() => {
    const loadUser = async () => {
      try {
        if (!checkAuth()) return;

        // If access token is expired, attempt a silent refresh first.
        // The Axios interceptor handles this automatically on API calls,
        // but we trigger it explicitly here so getCurrentUser() succeeds
        // on the first try without an extra 401 round-trip.
        const accessToken = getAccessToken();
        if (!accessToken || isTokenExpired(accessToken)) {
          await authService.refreshAccessToken();
        }

        const userData = await authService.getCurrentUser();
        setUser(userData);
        setIsAuthenticated(true);
      } catch (err) {
        console.error('Erreur lors du chargement de l\'utilisateur:', err);
        removeTokens();
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  /**
   * Periodic token validity check.
   * Detects token expiry mid-session and either silently refreshes
   * or logs the user out — keeps ProtectedRoute in sync without
   * waiting for a page reload.
   */
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(async () => {
      const token = getAccessToken();
      if (token && !isTokenExpired(token)) return; // still valid

      // Access token expired or missing — attempt silent refresh
      try {
        await authService.refreshAccessToken();
      } catch {
        // Refresh failed — session is over
        setUser(null);
        setIsAuthenticated(false);
        removeTokens();
      }
    }, 15_000); // check every 15 seconds

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  /**
   * Inscription d'un nouvel utilisateur
   * @param {object} userData - Données d'inscription
   * @returns {Promise} Résultat de l'inscription
   */
  const register = async (userData) => {
    try {
      setError(null);
      const response = await authService.register(userData);
      return { success: true, data: response };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  /**
   * Connexion d'un utilisateur
   * @param {string} username - Email ou username
   * @param {string} password - Mot de passe
   * @returns {Promise} Résultat de la connexion
   */
  const login = async (username, password) => {
    try {
      setError(null);
      setLoading(true);
      
      // Appeler le service de login
      const response = await authService.login(username, password);
      
      // Récupérer le profil complet
      const userData = await authService.getCurrentUser();
      
      setUser(userData);
      setIsAuthenticated(true);
      
      return { success: true, data: response };
    } catch (err) {
      setError(err.message);
      setUser(null);
      setIsAuthenticated(false);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Déconnexion de l'utilisateur
   */
  const logout = () => {
    authService.logout();
    setUser(null);
    setIsAuthenticated(false);
    setError(null);
  };

  /**
   * Mettre à jour le profil utilisateur
   * @param {object} profileData - Nouvelles données du profil
   * @returns {Promise} Résultat de la mise à jour
   */
  const updateUserProfile = async (profileData) => {
    try {
      setError(null);
      const updatedUser = await authService.updateProfile(profileData);
      setUser(updatedUser);
      return { success: true, data: updatedUser };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  /**
   * Rafraîchir les données utilisateur
   * Utile après une mise à jour externe
   */
  const refreshUser = async () => {
    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
      return { success: true, data: userData };
    } catch (err) {
      console.error('Erreur lors du rafraîchissement:', err);
      return { success: false, error: err.message };
    }
  };

  // Valeur du contexte fournie à tous les enfants
  const value = {
    user,
    isAuthenticated,
    loading,
    error,
    register,
    login,
    logout,
    updateUserProfile,
    refreshUser,
    setError, // Pour effacer les erreurs manuellement
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
