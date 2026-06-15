import AppShell from '@/src/features/navigation/components/AppShell';
import ProfileCareerSignalsScreen from '@/src/features/profile/components/ProfileCareerSignalsScreen';

export default function ProfileCareerRoute() {
  return (
    <AppShell title="Career signals" showBackButton>
      <ProfileCareerSignalsScreen />
    </AppShell>
  );
}
