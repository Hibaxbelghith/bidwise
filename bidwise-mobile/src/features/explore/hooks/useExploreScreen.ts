import { useMemo } from 'react';
import { useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useOpportunitiesList } from '@/src/features/opportunities/hooks/useOpportunitiesList';
import type { BidWiseProfile, ProfileUser } from '@/src/features/profile/types';

import type { ExploreBannerMode } from '../components/ExploreBanner';

const isTenderOnlyProfile = (profile?: BidWiseProfile) => {
  const types = Array.isArray(profile?.opportunity_types) ? profile.opportunity_types : [];
  return types.length === 1 && types[0] === 'CALLS_FOR_TENDER';
};

export function useExploreScreen() {
  const router = useRouter();
  const { isAuthenticated, loading: authLoading, user } = useAuth();
  const typedUser = user as ProfileUser | null;
  const profile = typedUser?.profil;

  const tenderOnly = isTenderOnlyProfile(profile);
  const opportunities = useOpportunitiesList({
    ready: !authLoading,
    initialTypeFilter: tenderOnly ? 'PROJET' : 'ALL',
  });

  const completionScore = Number(profile?.profile_completion?.score ?? 0);
  const hasResume = Boolean(profile?.active_resume);
  const hasRecommendationReadyProfile = completionScore >= 60;

  const bannerMode: ExploreBannerMode = useMemo(() => {
    if (tenderOnly) return 'tender';
    if (!isAuthenticated) return 'guest';
    if (!hasRecommendationReadyProfile) return 'incomplete_profile';
    if (!hasResume) return 'missing_cv';
    return 'ready';
  }, [hasRecommendationReadyProfile, hasResume, isAuthenticated, tenderOnly]);

  const bannerPrimaryLabel = useMemo(() => {
    switch (bannerMode) {
      case 'guest':
        return 'Quick login';
      case 'incomplete_profile':
        return 'Complete profile';
      case 'missing_cv':
        return 'Open profile';
      case 'ready':
      case 'tender':
      default:
        return tenderOnly ? 'Browse tenders' : 'See Matches';
    }
  }, [bannerMode, tenderOnly]);

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
      case 'tender':
      default:
        router.push(tenderOnly ? '/explore' : '/for-you');
    }
  };

  return {
    isAuthenticated,
    authLoading,
    profile,
    tenderOnly,
    bannerMode,
    bannerPrimaryLabel,
    onBannerAction: handleBannerAction,
    ...opportunities,
  };
}
