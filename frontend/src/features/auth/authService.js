/**
 * Auth service — passwordless authentication (OTP + Google OAuth2).
 */

import api from '../../lib/api';
import { saveTokens, removeTokens, getRefreshToken } from '../../lib/tokenManager';

// ── Passwordless OTP ──────────────────────────────────────

/**
 * Request a one-time password for the given email.
 * Backend sends a 6-digit code; the response is always 200 to
 * prevent user-enumeration.
 * @param {string} email
 * @returns {Promise<object>} { message }
 */
export const requestOTP = async (email) => {
  try {
    const response = await api.post('/auth/passwordless/request/', {
      email,
      client_type: 'web',
    });
    return response.data;
  } catch (error) {
    const errorMessage =
      error.response?.data?.detail ||
      error.response?.data?.email?.[0] ||
      'Erreur lors de l\'envoi du code';
    throw new Error(errorMessage);
  }
};

/**
 * Verify a 6-digit OTP and obtain JWT tokens.
 * Also stores tokens in localStorage via saveTokens().
 * @param {string} email
 * @param {string} otp - 6-digit code
 * @returns {Promise<object>} { access, refresh, is_new_user }
 */
export const verifyOTP = async (email, otp) => {
  try {
    const response = await api.post('/auth/passwordless/verify/', { email, otp });
    const { access, refresh } = response.data;
    saveTokens(access, refresh);
    return response.data;
  } catch (error) {
    const errorMessage =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      'Code invalide ou expiré';
    throw new Error(errorMessage);
  }
};

// ── Google OAuth2 ─────────────────────────────────────────

/**
 * Exchange a Google id_token for BidWise JWT tokens.
 * @param {string} idToken - The credential returned by Google Identity Services
 * @returns {Promise<object>} { access, refresh, is_new_user }
 */
export const googleLogin = async (idToken) => {
  try {
    const response = await api.post('/auth/google/', { id_token: idToken });
    const { access, refresh } = response.data;
    saveTokens(access, refresh);
    return response.data;
  } catch (error) {
    const errorMessage =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      'Google authentication failed';
    throw new Error(errorMessage);
  }
};

// ── Session management ───────────────────────────────────

/**
 * Déconnecter l'utilisateur.
 * Blacklists the refresh token server-side, then removes tokens locally.
 */
export const logout = async () => {
  try {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await api.post('/auth/logout/', { refresh: refreshToken });
    }
  } catch {
    // Best-effort: even if backend call fails, clear tokens locally
  } finally {
    removeTokens();
  }
};

/**
 * Obtenir les données de l'utilisateur connecté
 * @returns {Promise<object>} Données du profil utilisateur
 * @throws {Error} Erreur de récupération
 */
export const getCurrentUser = async (config = {}) => {
  try {
    const response = await api.get('/profile/me/', config);
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.detail || 
                        'Erreur lors de la récupération du profil';
    throw new Error(errorMessage);
  }
};

/**
 * Mettre à jour le profil utilisateur
 * @param {object} profileData - Données à mettre à jour
 *   - first_name: string (optionnel)
 *   - last_name: string (optionnel)
 *   - competences: string[] (optionnel)
 *   - domaines_interet: string[] (optionnel)
 *   - preferred_locations: string[] (optionnel)
 *   - work_mode_preferences: string[] (optionnel)
 *   - employment_types: string[] (optionnel)
 *   - niveau_experience: string (optionnel)
 *   - bio: string (optionnel)
 * @returns {Promise<object>} Profil mis à jour
 * @throws {Error} Erreur de mise à jour
 */
export const updateProfile = async (profileData) => {
  try {
    const response = await api.put('/profile/me/', profileData);
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.detail || 
                        'Erreur lors de la mise à jour du profil';
    throw new Error(errorMessage);
  }
};

/**
 * Rafraîchir le token d'accès
 * Utilise le refresh token pour obtenir un nouveau access token
 * @returns {Promise<object>} Nouvelle réponse avec tokens
 * @throws {Error} Erreur de rafraîchissement
 */
export const refreshAccessToken = async () => {
  try {
    const refreshToken = getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('Pas de refresh token disponible');
    }
    
    const response = await api.post('/auth/refresh/', {
      refresh: refreshToken
    });
    
    // Sauvegarder le nouveau access token
    const { access, refresh } = response.data;
    saveTokens(access, refresh || refreshToken);
    
    return response.data;
  } catch (error) {
    // Si le refresh échoue, supprimer les tokens
    removeTokens();
    const errorMessage = error.response?.data?.detail || 
                        'Session expirée, veuillez vous reconnecter';
    throw new Error(errorMessage);
  }
};

/**
 * Demander un reset de mot de passe
 * @param {string} email - Email du compte
 * @returns {Promise<object>} Message de confirmation
 * @throws {Error} Erreur de la demande
 */
export const requestPasswordReset = async (email) => {
  try {
    const response = await api.post('/auth/password-reset/', { email });
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.detail || 
                        'Erreur lors de la demande de reset';
    throw new Error(errorMessage);
  }
};

/**
 * Confirmer le reset de mot de passe
 * @param {string} uid - UID encodé (depuis l'email)
 * @param {string} token - Token (depuis l'email)
 * @param {string} newPassword - Nouveau mot de passe
 * @param {string} newPassword2 - Confirmation du nouveau mot de passe
 * @returns {Promise<object>} Message de confirmation
 * @throws {Error} Erreur de confirmation
 */
export const confirmPasswordReset = async (uid, token, newPassword, newPassword2) => {
  try {
    const response = await api.post('/auth/password-reset-confirm/', {
      uid,
      token,
      new_password: newPassword,
      new_password2: newPassword2
    });
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.detail || 
                        'Erreur lors de la réinitialisation du mot de passe';
    throw new Error(errorMessage);
  }
};
