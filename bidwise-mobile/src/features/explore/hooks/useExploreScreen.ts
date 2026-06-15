import { useMemo } from 'react';
import { useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useOpportunitiesList } from '@/src/features/opportunities/hooks/useOpportunitiesList';
import type { ProfileUser } from '@/src/features/profile/types';

import type { ExploreBannerMode } from '../components/ExploreBanner';

export function useExploreScreen() {
  const router = useRouter();
  const { isAuthenticated, loading: authLoading, user } = useAuth();
  const typedUser = user as ProfileUser | null;
  const profile = typedUser?.profil;

  const opportunities = useOpportunitiesList({ ready: !authLoading });

  const completionScore = Number(profile?.profile_completion?.score ?? 0);
  const hasResume = Boolean(profile?.active_resume);

  const bannerMode: ExploreBannerMode = useMemo(() => {
    if (!isAuthenticated) return 'guest';
    if (!profile?.onboarding_completed || completionScore < 60) return 'incomplete_profile';
    if (!hasResume) return 'missing_cv';
    return 'ready';
  }, [completionScore, hasResume, isAuthenticated, profile?.onboarding_completed]);

  const bannerPrimaryLabel = useMemo(() => {
    switch (bannerMode) {
      case 'guest':
        return 'Quick login';
      case 'incomplete_profile':
        return 'Complete profile';
      case 'missing_cv':
        return 'Open profile';
      case 'ready':
      default:
        return 'See Matches';
    }
  }, [bannerMode]);

  const handleBannerAction = () => {
    switch (bannerMode) {
      case 'guest':
        router.push('/login');
        return;
      case 'incomplete_profile':
      case 'missing_cv':
        router.push('/profile');
        return;
      case 'ready':
      default:
        router.push('/for-you');
    }
  };

  return {
    isAuthenticated,
    authLoading,
    profile,
    bannerMode,
    bannerPrimaryLabel,
    handleBannerAction,
    ...opportunities,
  };
}
