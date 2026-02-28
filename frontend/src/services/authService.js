/**
 * Service d'authentification
 * Centralise toutes les requêtes liées à l'authentification
 */

import api from './api';
import { saveTokens, removeTokens, getRefreshToken } from '../utils/tokenManager';

/**
 * Inscrire un nouvel utilisateur
 * @param {object} userData - Données d'inscription
 *   - email: string (requis, unique)
 *   - username: string (requis, unique)
 *   - password: string (requis)
 *   - password2: string (confirmation, requis)
 *   - first_name: string (requis)
 *   - last_name: string (requis)
 *   - account_type: string (CANDIDAT ou ORGANISATION, requis)
 * @returns {Promise<object>} Réponse backend avec user data
 * @throws {Error} Erreur d'inscription
 */
export const register = async (userData) => {
  try {
    const response = await api.post('/auth/register/', userData);
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.detail || 
                        error.response?.data?.email?.[0] ||
                        error.response?.data?.username?.[0] ||
                        error.response?.data?.password?.[0] ||
                        'Erreur lors de l\'inscription';
    throw new Error(errorMessage);
  }
};

/**
 * Connecter un utilisateur
 * @param {string} username - Email ou username
 * @param {string} password - Mot de passe
 * @returns {Promise<object>} User data après connexion
 * @throws {Error} Erreur de connexion
 */
export const login = async (username, password) => {
  try {
    const response = await api.post('/auth/login/', { username, password });
    
    // Sauvegarder les tokens
    const { access, refresh } = response.data;
    saveTokens(access, refresh);
    
    // Retourner les données utilisateur
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.detail || 
                        'Identifiants invalides';
    throw new Error(errorMessage);
  }
};

/**
 * Déconnecter l'utilisateur
 * (Supprime les tokens localement - logout est stateless côté backend)
 */
export const logout = () => {
  try {
    removeTokens();
  } catch (error) {
    console.error('Erreur lors de la déconnexion:', error);
  }
};

/**
 * Obtenir les données de l'utilisateur connecté
 * @returns {Promise<object>} Données du profil utilisateur
 * @throws {Error} Erreur de récupération
 */
export const getCurrentUser = async () => {
  try {
    const response = await api.get('/profile/me/');
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
 *   - competences: string (optionnel)
 *   - domaines_interet: string (optionnel)
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
