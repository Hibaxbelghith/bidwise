import AppShell from '@/src/features/navigation/components/AppShell';
import ProfilePreferencesScreen from '@/src/features/profile/components/ProfilePreferencesScreen';

export default function ProfilePreferencesRoute() {
  return (
    <AppShell title="Preferences" showBackButton>
      <ProfilePreferencesScreen />
    </AppShell>
  );
}
