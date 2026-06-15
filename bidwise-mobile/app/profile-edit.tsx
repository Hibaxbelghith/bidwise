import AppShell from '@/src/features/navigation/components/AppShell';
import ProfileEditScreen from '@/src/features/profile/components/ProfileEditScreen';

export default function ProfileEditRoute() {
  return (
    <AppShell title="Edit Profile" showBackButton>
      <ProfileEditScreen />
    </AppShell>
  );
}
