import ProfileSection from '@/src/features/profile/components/ProfileSection';
import ProfileEditorPage from '@/src/features/profile/components/ProfileEditorPage';
import ProfileFormField from '@/src/features/profile/components/ProfileFormField';
import PreferenceChipGroup from '@/src/features/profile/components/PreferenceChipGroup';
import { useProfileEditor } from '@/src/features/profile/hooks/useProfileEditor';
import { EXPERIENCE_LEVEL_OPTIONS } from '@/src/features/profile/utils/profileEditorState';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

export default function ProfileBasicInformationScreen() {
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const colors = {
    tint: tintColor,
    border: borderColor,
    text: textColor,
    muted: mutedColor,
    card: cardColor,
  };

  const {
    editorState,
    fieldErrors,
    formError,
    successMessage,
    loading,
    saving,
    isDirty,
    setFormField,
    handleSave,
    refreshProfile,
  } = useProfileEditor();

  return (
    <ProfileEditorPage
      title="Basic information"
      subtitle="Update your identity and experience level so your profile reads clearly to recruiters."
      loading={loading}
      onRefresh={refreshProfile}
      onSave={handleSave}
      saving={saving}
      isDirty={isDirty}
      formError={formError}
      successMessage={successMessage}
    >
      <ProfileSection
        title="Identity"
        description="The essentials shown across your candidate profile."
        defaultOpen
        colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
      >
        <ProfileFormField
          label="First name"
          value={editorState.formData.firstName}
          onChangeText={(value) => setFormField('firstName', value)}
          placeholder="First name"
          error={fieldErrors.firstName}
          textColor={textColor}
          mutedColor={mutedColor}
          borderColor={borderColor}
          cardColor={cardColor}
        />
        <ProfileFormField
          label="Last name"
          value={editorState.formData.lastName}
          onChangeText={(value) => setFormField('lastName', value)}
          placeholder="Last name"
          error={fieldErrors.lastName}
          textColor={textColor}
          mutedColor={mutedColor}
          borderColor={borderColor}
          cardColor={cardColor}
        />
      </ProfileSection>

      <ProfileSection
        title="Experience"
        description="Help BidWise understand your current seniority."
        defaultOpen
        colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
      >
        <PreferenceChipGroup
          options={EXPERIENCE_LEVEL_OPTIONS}
          value={editorState.formData.experienceLevel ? [editorState.formData.experienceLevel] : []}
          onChange={(values) => setFormField('experienceLevel', values[values.length - 1] || '')}
          colors={colors}
          compact
        />
        <ProfileFormField
          label="Years of experience"
          value={editorState.formData.yearsOfExperience}
          onChangeText={(value) => setFormField('yearsOfExperience', value.replace(/[^\d]/g, ''))}
          placeholder="0"
          keyboardType="number-pad"
          error={fieldErrors.yearsOfExperience}
          textColor={textColor}
          mutedColor={mutedColor}
          borderColor={borderColor}
          cardColor={cardColor}
        />
      </ProfileSection>
    </ProfileEditorPage>
  );
}
