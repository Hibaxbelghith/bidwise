import { StyleSheet, Text, View } from 'react-native';

import PreferenceChipGroup from '@/src/features/profile/components/PreferenceChipGroup';
import ProfileAutocompleteInput from '@/src/features/profile/components/ProfileAutocompleteInput';
import ProfileEditorPage from '@/src/features/profile/components/ProfileEditorPage';
import ProfileSection from '@/src/features/profile/components/ProfileSection';
import { BUSINESS_FAMILY_OPTIONS } from '@/src/features/profile/constants/profileOptions';
import { useProfileEditor } from '@/src/features/profile/hooks/useProfileEditor';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

const isCallsForTenderOnly = (values: string[]) =>
  values.length === 1 && values[0] === 'CALLS_FOR_TENDER';

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
  const tenderOnly = isCallsForTenderOnly(editorState.opportunityTypes);

  return (
    <ProfileEditorPage
      title="Career signals"
      subtitle={tenderOnly ? 'Keep optional sectors ready for tender filtering.' : 'Keep your skills, target roles, and sectors aligned so recommendations stay relevant.'}
      loading={loading}
      onRefresh={refreshProfile}
      onSave={handleSave}
      saving={saving}
      isDirty={isDirty}
      formError={formError}
      successMessage={successMessage}
    >
      <ProfileSection
        title={tenderOnly ? 'Tender filters' : 'Matching signals'}
        description={tenderOnly ? 'Sectors are optional and help you filter public tenders faster.' : 'These signals feed recommendation and recruiter discovery.'}
        defaultOpen
        colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
      >
        {!tenderOnly ? (
        <>
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
        </>
        ) : null}
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
