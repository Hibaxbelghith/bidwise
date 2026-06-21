import { Redirect } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import AppShell from '@/src/features/navigation/components/AppShell';
import ForYouScreen from '@/src/features/opportunities/components/ForYouScreen';

function isCallsForTenderOnlyProfile(profile?: { opportunity_types?: string[] } | null) {
  const types = Array.isArray(profile?.opportunity_types) ? profile.opportunity_types : [];
  return types.length === 1 && types[0] === 'CALLS_FOR_TENDER';
}

export default function ForYouRoute() {
  const { user } = useAuth();

  if (isCallsForTenderOnlyProfile(user?.profil)) {
    return <Redirect href="/explore" />;
  }

  return (
    <AppShell title="For You" currentTab="for-you">
      <ForYouScreen embedded />
    </AppShell>
  );
}
