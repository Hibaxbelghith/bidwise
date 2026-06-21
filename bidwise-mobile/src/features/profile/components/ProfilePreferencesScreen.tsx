import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import PreferenceChipGroup from '@/src/features/profile/components/PreferenceChipGroup';
import ProfileEditorPage from '@/src/features/profile/components/ProfileEditorPage';
import ProfileFormField from '@/src/features/profile/components/ProfileFormField';
import ProfileSection from '@/src/features/profile/components/ProfileSection';
import SalaryExpectationField from '@/src/features/profile/components/SalaryExpectationField';
import {
  getEmploymentTypeOptionsForOpportunityTypes,
  ONBOARDING_OPPORTUNITY_TYPE_OPTIONS,
  TUNISIAN_LOCATION_OPTIONS,
  WORK_MODE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';
import { useProfileEditor } from '@/src/features/profile/hooks/useProfileEditor';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

const isCallsForTenderOnly = (values: string[]) =>
  values.length === 1 && values[0] === 'CALLS_FOR_TENDER';

export default function ProfilePreferencesScreen() {
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
    locationInput,
    setLocationInput,
    setFormField,
    setStateField,
    addPreferredLocation,
    removePreferredLocation,
    handleSave,
    refreshProfile,
  } = useProfileEditor();

  const selectedLocationKeys = new Set(
    editorState.preferredLocations.map((item) => item.toLowerCase()),
  );

  const filteredLocationSuggestions = TUNISIAN_LOCATION_OPTIONS.filter((location) => {
    if (selectedLocationKeys.has(location.toLowerCase())) return false;
    if (!locationInput.trim()) return true;
    return location.toLowerCase().includes(locationInput.trim().toLowerCase());
  }).slice(0, 8);
  const employmentTypeOptions = getEmploymentTypeOptionsForOpportunityTypes(
    editorState.opportunityTypes,
  );
  const visibleEmploymentTypeValues = new Set(
    employmentTypeOptions.map((option) => option.value),
  );
  const visibleEmploymentTypes = editorState.employmentTypes.filter((value) =>
    visibleEmploymentTypeValues.has(value),
  );
  const tenderOnly = isCallsForTenderOnly(editorState.opportunityTypes);
  const setOpportunityTypes = (values: string[]) => {
    const allowedEmploymentTypes = new Set(
      getEmploymentTypeOptionsForOpportunityTypes(values).map((option) => option.value),
    );
    setStateField('opportunityTypes', values);
    setStateField(
      'employmentTypes',
      isCallsForTenderOnly(values)
        ? []
        : editorState.employmentTypes.filter((value) => allowedEmploymentTypes.has(value)),
    );
  };

  return (
    <ProfileEditorPage
      title={tenderOnly ? 'Tender preferences' : 'Preferences'}
      subtitle={tenderOnly ? 'Choose the public tender filters BidWise should open first.' : 'Choose the opportunity conditions you want BidWise to prioritize.'}
      loading={loading}
      onRefresh={refreshProfile}
      onSave={handleSave}
      saving={saving}
      isDirty={isDirty}
      formError={formError}
      successMessage={successMessage}
    >
      <ProfileSection
        title={tenderOnly ? 'Tender filters' : 'Opportunity fit'}
        description={tenderOnly ? 'Calls for tender use type and optional region filters only.' : 'What kind of opportunities should appear first.'}
        defaultOpen
        colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
      >
        <View style={styles.fieldBlock}>
          <Text style={[styles.fieldLabel, { color: textColor }]}>Opportunity types</Text>
          <PreferenceChipGroup
            options={ONBOARDING_OPPORTUNITY_TYPE_OPTIONS}
            value={editorState.opportunityTypes}
            onChange={setOpportunityTypes}
            colors={colors}
          />
        </View>
        <View style={styles.fieldBlock}>
          <Text style={[styles.fieldLabel, { color: textColor }]}>
            {tenderOnly ? 'Preferred tender regions' : 'Preferred locations'}
          </Text>
          <View style={styles.locationInputRow}>
            <TextInput
              value={locationInput}
              onChangeText={setLocationInput}
              onSubmitEditing={() => addPreferredLocation(locationInput)}
              placeholder="Tunis, Sfax, Sousse..."
              placeholderTextColor={mutedColor}
              style={[
                styles.input,
                {
                  flex: 1,
                  color: textColor,
                  backgroundColor: cardColor,
                  borderColor: fieldErrors.preferredLocations ? '#dc2626' : borderColor,
                },
              ]}
            />
            <Pressable
              accessibilityRole="button"
              onPress={() => addPreferredLocation(locationInput)}
              style={[
                styles.addButton,
                { backgroundColor: tintColor, opacity: locationInput.trim() ? 1 : 0.45 },
              ]}
            >
              <Text style={styles.addButtonText}>+</Text>
            </Pressable>
          </View>
          <View style={styles.quickWrap}>
            {filteredLocationSuggestions.map((location) => (
              <Pressable
                key={location}
                accessibilityRole="button"
                onPress={() => addPreferredLocation(location)}
                style={[styles.quickChip, { backgroundColor: cardColor, borderColor }]}
              >
                <Text style={[styles.quickChipText, { color: textColor }]}>{location}</Text>
              </Pressable>
            ))}
          </View>
          {editorState.preferredLocations.length ? (
            <View style={styles.selectedWrap}>
              {editorState.preferredLocations.map((location) => (
                <Pressable
                  key={location}
                  accessibilityRole="button"
                  onPress={() => removePreferredLocation(location)}
                  style={[styles.selectedChip, { borderColor: tintColor, backgroundColor: `${tintColor}18` }]}
                >
                  <Text style={[styles.selectedChipText, { color: tintColor }]}>{location} ×</Text>
                </Pressable>
              ))}
            </View>
          ) : null}
          {fieldErrors.preferredLocations ? (
            <Text style={styles.fieldError}>{fieldErrors.preferredLocations}</Text>
          ) : null}
        </View>
      </ProfileSection>

      {!tenderOnly ? (
      <ProfileSection
        title="Work conditions"
        description="Work mode, contract preferences, and salary expectations."
        defaultOpen
        colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
      >
        <View style={styles.fieldBlock}>
          <Text style={[styles.fieldLabel, { color: textColor }]}>Work modes</Text>
          <PreferenceChipGroup
            options={WORK_MODE_OPTIONS}
            value={editorState.workModePreferences}
            onChange={(values) => setStateField('workModePreferences', values)}
            colors={colors}
            compact
          />
        </View>
        <View style={styles.fieldBlock}>
          <Text style={[styles.fieldLabel, { color: textColor }]}>Employment types</Text>
          <PreferenceChipGroup
            options={employmentTypeOptions}
            value={visibleEmploymentTypes}
            onChange={(values) => setStateField('employmentTypes', values)}
            colors={colors}
            compact
          />
        </View>
        <SalaryExpectationField
          amount={editorState.formData.salaryMinExpectation}
          period={editorState.formData.salaryPeriod}
          onAmountChange={(value) => setFormField('salaryMinExpectation', value)}
          onPeriodChange={(value) => setFormField('salaryPeriod', value)}
          colors={colors}
        />
        <ProfileFormField
          label="Maximum expected salary"
          value={editorState.formData.salaryMaxExpectation}
          onChangeText={(value) => setFormField('salaryMaxExpectation', value.replace(/[^\d]/g, ''))}
          placeholder="Optional max"
          keyboardType="number-pad"
          error={fieldErrors.salaryRange}
          textColor={textColor}
          mutedColor={mutedColor}
          borderColor={borderColor}
          cardColor={cardColor}
        />
      </ProfileSection>
      ) : null}
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
  input: {
    borderRadius: 12,
    borderWidth: 1,
    fontSize: 15,
    paddingHorizontal: 14,
    paddingVertical: 11,
  },
  locationInputRow: {
    flexDirection: 'row',
    gap: 8,
  },
  addButton: {
    width: 46,
    height: 46,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addButtonText: {
    color: '#ffffff',
    fontSize: 22,
    fontWeight: '800',
  },
  quickWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  quickChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  quickChipText: {
    fontSize: 13,
    fontWeight: '600',
  },
  selectedWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  selectedChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  selectedChipText: {
    fontSize: 13,
    fontWeight: '700',
  },
  fieldError: {
    color: '#dc2626',
    fontSize: 12,
    lineHeight: 17,
  },
});
