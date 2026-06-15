import AppShell from '@/src/features/navigation/components/AppShell';
import ProfileResumeScreen from '@/src/features/profile/components/ProfileResumeScreen';

export default function ProfileResumeRoute() {
  return (
    <AppShell title="Resume" showBackButton>
      <ProfileResumeScreen />
    </AppShell>
  );
}
