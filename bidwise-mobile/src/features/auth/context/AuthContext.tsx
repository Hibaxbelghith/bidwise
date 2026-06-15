import React, { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import {
  googleLogin as googleLoginService,
  logoutServer,
  verifyOTP as verifyOTPService,
} from '@/src/features/auth/services/authService';
import { getProfile } from '@/src/features/profile/services/profileService';
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from '@/src/shared/services/tokenStorage';
import type { ProfileUser } from '@/src/features/profile/types';

interface AuthContextType {
  user: ProfileUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  loginWithOTP: (email: string, otpCode: string) => Promise<{ is_new_user: boolean; onboarding_completed: boolean }>;
  loginWithGoogle: (idToken: string) => Promise<{ is_new_user: boolean; onboarding_completed: boolean }>;
  logout: () => Promise<void>;
  loadUserProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<ProfileUser | null>(null);
  const [loading, setLoading] = useState(true);

  // On app start, check for existing token and load profile
  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessToken();
        if (token) {
          const profile = await getProfile();
          setUser(profile);
        }
      } catch {
        // token expired / invalid — stay logged out
        await clearTokens();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const loginWithOTP = useCallback(async (email: string, otpCode: string) => {
    const data = await verifyOTPService(email, otpCode);
    await setTokens(data.access, data.refresh);

    const profile = await getProfile();
    setUser(profile);

    const onboarding_completed = profile?.profil?.onboarding_completed ?? false;
    return { is_new_user: data.is_new_user, onboarding_completed };
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const data = await googleLoginService(idToken);
    await setTokens(data.access, data.refresh);

    const profile = await getProfile();
    setUser(profile);

    const onboarding_completed = profile?.profil?.onboarding_completed ?? false;
    return { is_new_user: data.is_new_user, onboarding_completed };
  }, []);

  const loadUserProfile = useCallback(async () => {
    const profile = await getProfile();
    setUser(profile);
  }, []);

  const logout = useCallback(async () => {
    try {
      const refresh = await getRefreshToken();
      if (refresh) {
        await logoutServer(refresh);
      }
    } catch {
      // Best-effort: clear tokens locally even if server call fails
    } finally {
      await clearTokens();
      setUser(null);
    }
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    loading,
    loginWithOTP,
    loginWithGoogle,
    logout,
    loadUserProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
