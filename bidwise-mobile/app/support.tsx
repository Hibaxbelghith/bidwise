import AppShell from '@/src/features/navigation/components/AppShell';
import SupportScreen from '@/src/features/support/components/SupportScreen';

export default function SupportRoute() {
  return (
    <AppShell title="Support" showBackButton>
      <SupportScreen />
    </AppShell>
  );
}
