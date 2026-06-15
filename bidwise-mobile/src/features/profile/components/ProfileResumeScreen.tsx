import ProfileEditorPage from '@/src/features/profile/components/ProfileEditorPage';
import ProfileSection from '@/src/features/profile/components/ProfileSection';
import ResumeSection from '@/src/features/profile/components/ResumeSection';
import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

export default function ProfileResumeScreen() {
  const { user, loadUserProfile, loading } = useAuth();
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  return (
    <ProfileEditorPage
      title="Resume"
      subtitle="Manage the CV used for direct applications, AI extraction, and candidate discovery."
      loading={loading}
      onRefresh={loadUserProfile}
      onSave={async () => true}
      saving={false}
      isDirty={false}
      saveLabel="Up to date"
      showSaveBar={false}
    >
      <ProfileSection
        title="Active resume"
        description="Upload, replace, open, or remove your current CV."
        defaultOpen
        colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
      >
        <ResumeSection
          profile={user?.profil}
          onChanged={loadUserProfile}
          colors={{
            tint: tintColor,
            border: borderColor,
            text: textColor,
            muted: mutedColor,
            card: cardColor,
          }}
        />
      </ProfileSection>
    </ProfileEditorPage>
  );
}
