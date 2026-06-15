import AppShell from '@/src/features/navigation/components/AppShell';
import ProfileScreen from '@/src/features/profile/components/ProfileScreen';

export default function ProfileRoute() {
  return (
    <AppShell title="Profile" currentTab="profile">
      <ProfileScreen embedded />
    </AppShell>
  );
}
