import AppShell from '@/src/features/navigation/components/AppShell';
import SettingsScreen from '@/src/features/profile/components/SettingsScreen';

export default function SettingsRoute() {
  return (
    <AppShell title="Settings" showBackButton>
      <SettingsScreen />
    </AppShell>
  );
}
