import { Redirect } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';

import { useAuth } from '@/src/features/auth/context/AuthContext';

const hasStartedCandidateProfile = (score: unknown) => {
  const numericScore = Number(score);
  return Number.isFinite(numericScore) && numericScore > 0;
};

export default function Index() {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  const onboardingCompleted = Boolean(user?.profil?.onboarding_completed)
    || hasStartedCandidateProfile(user?.profil?.profile_completion?.score);

  if (!isAuthenticated) {
    return <Redirect href="/explore" />;
  }

  return <Redirect href={onboardingCompleted ? '/explore' : '/onboarding'} />;
}
