import AppShell from '@/src/features/navigation/components/AppShell';
import ProfileBasicInformationScreen from '@/src/features/profile/components/ProfileBasicInformationScreen';

export default function ProfileBasicRoute() {
  return (
    <AppShell title="Basic information" showBackButton>
      <ProfileBasicInformationScreen />
    </AppShell>
  );
}
