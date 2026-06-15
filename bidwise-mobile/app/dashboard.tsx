import DashboardScreen from '@/src/features/dashboard/components/DashboardScreen';
import AppShell from '@/src/features/navigation/components/AppShell';

export default function DashboardRoute() {
  return (
    <AppShell title="Dashboard" currentTab="dashboard">
      <DashboardScreen embedded />
    </AppShell>
  );
}
