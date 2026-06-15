import { StyleSheet, Text, View } from 'react-native';

import PreferenceChipGroup from '@/src/features/profile/components/PreferenceChipGroup';
import ProfileAutocompleteInput from '@/src/features/profile/components/ProfileAutocompleteInput';
import ProfileEditorPage from '@/src/features/profile/components/ProfileEditorPage';
import ProfileSection from '@/src/features/profile/components/ProfileSection';
import { BUSINESS_FAMILY_OPTIONS } from '@/src/features/profile/constants/profileOptions';
import { useProfileEditor } from '@/src/features/profile/hooks/useProfileEditor';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

export default function ProfileCareerSignalsScreen() {
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
    formError,
    successMessage,
    loading,
    saving,
    isDirty,
    setStateField,
    handleSave,
    refreshProfile,
  } = useProfileEditor();

  return (
    <ProfileEditorPage
      title="Career signals"
      subtitle="Keep your skills, target roles, and sectors aligned so recommendations stay relevant."
      loading={loading}
      onRefresh={refreshProfile}
      onSave={handleSave}
      saving={saving}
      isDirty={isDirty}
      formError={formError}
      successMessage={successMessage}
    >
      <ProfileSection
        title="Matching signals"
        description="These signals feed recommendation and recruiter discovery."
        defaultOpen
        colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
      >
        <ProfileAutocompleteInput
          label="Target roles"
          termType="role"
          value={editorState.targetRoles}
          onChange={(value) => setStateField('targetRoles', value)}
          placeholder="Frontend Developer, Data Analyst..."
          maxItems={5}
          colors={colors}
        />
        <ProfileAutocompleteInput
          label="Skills"
          termType="skill"
          value={editorState.skills}
          onChange={(value) => setStateField('skills', value)}
          placeholder="Python, React, SQL..."
          colors={colors}
        />
        <View style={styles.fieldBlock}>
          <Text style={[styles.fieldLabel, { color: textColor }]}>Sectors / Interests</Text>
          <PreferenceChipGroup
            options={BUSINESS_FAMILY_OPTIONS}
            value={editorState.interests}
            onChange={(value) => setStateField('interests', value.slice(0, 5))}
            colors={colors}
            compact
          />
        </View>
      </ProfileSection>
    </ProfileEditorPage>
  );
}

const styles = StyleSheet.create({
  fieldBlock: {
    gap: 10,
  },
  fieldLabel: {
    fontSize: 15,
    fontWeight: '700',
  },
});
