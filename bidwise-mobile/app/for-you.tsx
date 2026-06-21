import AppShell from '@/src/features/navigation/components/AppShell';
import ForYouScreen from '@/src/features/opportunities/components/ForYouScreen';

export default function ForYouRoute() {
  return (
    <AppShell title="For You" currentTab="for-you">
      <ForYouScreen embedded />
    </AppShell>
  );
}
