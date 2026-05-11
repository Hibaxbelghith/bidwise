/**
 * AuthContext - Contexte d'authentification global
 * Fournit l'état d'authentification à toute l'application
 */

import { createContext, useContext, useState, useEffect } from 'react';
import * as authService from './authService';
import { removeTokens } from '../../lib/tokenManager';

// Créer le contexte
const AuthContext = createContext(null);

/**
 * Hook personnalisé pour utiliser le contexte d'authentification
 * Utilisation: const { user, loginWithGoogle, logout } = useAuth();
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
   * Charger l'utilisateur au montage si un token existe.
   * Le refresh silencieux est géré uniquement par l'intercepteur Axios.
   */
  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await authService.getCurrentUser({ skipAuthRedirect: true });
        setUser(userData);
        setIsAuthenticated(true);
      } catch (err) {
        removeTokens();
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  // —— Passwordless OTP ————————————————————————————————————————————————

  /**
   * Request an OTP code for the given email.
   * @param {string} email
   * @returns {Promise<{ success: boolean, error?: string }>}
   */
  const requestOTP = async (email) => {
    try {
      setError(null);
      await authService.requestOTP(email);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  /**
   * Verify OTP, store tokens, load user profile.
   * @param {string} email
   * @param {string} otp - 6-digit code
   * @returns {Promise<{ success: boolean, is_new_user?: boolean, error?: string }>}
   */
  const verifyOTP = async (email, otp) => {
    try {
      setError(null);

      const response = await authService.verifyOTP(email, otp);

      // Tokens are already saved by authService.verifyOTP.
      // Now load the full user profile.
      const userData = await authService.getCurrentUser();
      setUser(userData);
      setIsAuthenticated(true);

      const onboarding_completed = userData?.profil?.onboarding_completed ?? false;
      return {
        success: true,
        is_new_user: response.is_new_user,
        onboarding_completed,
        user: userData,
      };
    } catch (err) {
      setError(err.message);
      setUser(null);
      setIsAuthenticated(false);
      return { success: false, error: err.message };
    }
  };

  // —— Google OAuth2 —————————————————————————————————————————————————————

  /**
   * Authenticate with a Google id_token, store tokens, load profile.
   * @param {string} idToken - credential from Google Identity Services
   * @returns {Promise<{ success: boolean, is_new_user?: boolean, error?: string }>}
   */
  const loginWithGoogle = async (idToken) => {
    try {
      setError(null);

      const response = await authService.googleLogin(idToken);

      // Tokens already saved by authService.googleLogin.
      const userData = await authService.getCurrentUser();
      setUser(userData);
      setIsAuthenticated(true);

      const onboarding_completed = userData?.profil?.onboarding_completed ?? false;
      return {
        success: true,
        is_new_user: response.is_new_user,
        onboarding_completed,
        user: userData,
      };
    } catch (err) {
      setError(err.message);
      setUser(null);
      setIsAuthenticated(false);
      return { success: false, error: err.message };
    }
  };

  // —— Legacy (kept until Phase 2 page cleanup) ————————————————

  /**
   * Déconnexion de l'utilisateur
   */
  const logout = async () => {
    await authService.logout();
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
    requestOTP,
    verifyOTP,
    loginWithGoogle,
    logout,
    updateUserProfile,
    refreshUser,
    setError,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
