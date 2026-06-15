import { Redirect } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';

import { useAuth } from '@/src/features/auth/context/AuthContext';

export default function Index() {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  const onboardingCompleted = user?.profil?.onboarding_completed ?? false;

  if (!isAuthenticated) {
    return <Redirect href="/explore" />;
  }

  return <Redirect href={onboardingCompleted ? '/explore' : '/onboarding'} />;
}
