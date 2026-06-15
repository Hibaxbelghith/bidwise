import { useMemo } from 'react';
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import PreferenceChipGroup from '@/src/features/profile/components/PreferenceChipGroup';
import ProfileAutocompleteInput from '@/src/features/profile/components/ProfileAutocompleteInput';
import ProfileSection from '@/src/features/profile/components/ProfileSection';
import SalaryExpectationField from '@/src/features/profile/components/SalaryExpectationField';
import {
  BUSINESS_FAMILY_OPTIONS,
  EMPLOYMENT_TYPE_OPTIONS,
  ONBOARDING_OPPORTUNITY_TYPE_OPTIONS,
  TUNISIAN_LOCATION_OPTIONS,
  WORK_MODE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';
import { useProfileEditor } from '@/src/features/profile/hooks/useProfileEditor';
import { EXPERIENCE_LEVEL_OPTIONS } from '@/src/features/profile/utils/profileEditorState';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

function Field({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  error,
  textColor,
  mutedColor,
  borderColor,
  cardColor,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  placeholder: string;
  keyboardType?: 'default' | 'number-pad';
  error?: string;
  textColor: string;
  mutedColor: string;
  borderColor: string;
  cardColor: string;
}) {
  return (
    <View style={styles.fieldBlock}>
      <Text style={[styles.fieldLabel, { color: textColor }]}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={mutedColor}
        keyboardType={keyboardType}
        inputMode={keyboardType === 'number-pad' ? 'numeric' : 'text'}
        style={[
          styles.input,
          {
            color: textColor,
            backgroundColor: cardColor,
            borderColor: error ? '#dc2626' : borderColor,
          },
        ]}
      />
      {error ? <Text style={styles.fieldError}>{error}</Text> : null}
    </View>
  );
}

export default function ProfileEditScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { loadUserProfile, loading: authLoading, isAuthenticated } = useAuth();
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');
  const backgroundColor = useThemeColor({}, 'background');

  const colors = useMemo(
    () => ({
      tint: tintColor,
      border: borderColor,
      text: textColor,
      muted: mutedColor,
      card: cardColor,
    }),
    [borderColor, cardColor, mutedColor, textColor, tintColor],
  );

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
  } = useProfileEditor();

  const selectedLocationKeys = new Set(
    editorState.preferredLocations.map((item) => item.toLowerCase()),
  );

  const filteredLocationSuggestions = TUNISIAN_LOCATION_OPTIONS.filter((location) => {
    if (selectedLocationKeys.has(location.toLowerCase())) return false;
    if (!locationInput.trim()) return true;
    return location.toLowerCase().includes(locationInput.trim().toLowerCase());
  }).slice(0, 8);

  if (!authLoading && !isAuthenticated) {
    return (
      <View style={[styles.centeredState, { backgroundColor }]}>
        <Text style={[styles.stateTitle, { color: textColor }]}>Login required</Text>
        <Text style={[styles.stateText, { color: mutedColor }]}>
          You need to sign in before editing your profile.
        </Text>
        <Pressable
          accessibilityRole="button"
          onPress={() => router.replace('/login')}
          style={[styles.primaryInlineButton, { backgroundColor: tintColor }]}
        >
          <Text style={styles.primaryInlineButtonText}>Go to login</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor }]}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingBottom: 126 + Math.max(insets.bottom, 12) },
        ]}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={loadUserProfile}
            tintColor={tintColor}
            colors={[tintColor]}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.headerBlock}>
          <Text style={[styles.title, { color: textColor }]}>Edit profile</Text>
          <Text style={[styles.subtitle, { color: mutedColor }]}>
            Update the signals that power recommendations, matching, and recruiter visibility.
          </Text>
        </View>

        {formError ? (
          <View style={[styles.feedbackCard, { backgroundColor: cardColor, borderColor: '#fecaca' }]}>
            <Text style={[styles.feedbackTitle, { color: textColor }]}>Unable to save profile</Text>
            <Text style={[styles.feedbackText, { color: mutedColor }]}>{formError}</Text>
          </View>
        ) : null}

        {successMessage ? (
          <View style={[styles.feedbackCard, { backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' }]}>
            <Text style={[styles.feedbackTitle, { color: '#166534' }]}>Profile updated</Text>
            <Text style={[styles.feedbackText, { color: '#166534' }]}>{successMessage}</Text>
          </View>
        ) : null}

        <ProfileSection
          title="Basic Information"
          description="Identity and experience level."
          defaultOpen
          colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
        >
          <Field
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
          <Field
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
          <View style={styles.fieldBlock}>
            <Text style={[styles.fieldLabel, { color: textColor }]}>Experience level</Text>
            <PreferenceChipGroup
              options={EXPERIENCE_LEVEL_OPTIONS}
              value={editorState.formData.experienceLevel ? [editorState.formData.experienceLevel] : []}
              onChange={(values) =>
                setFormField('experienceLevel', values[values.length - 1] || '')
              }
              colors={colors}
              compact
            />
          </View>
          <Field
            label="Years of experience"
            value={editorState.formData.yearsOfExperience}
            onChangeText={(value) =>
              setFormField('yearsOfExperience', value.replace(/[^\d]/g, ''))
            }
            placeholder="0"
            keyboardType="number-pad"
            error={fieldErrors.yearsOfExperience}
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
          />
        </ProfileSection>

        <ProfileSection
          title="Preferences"
          description="Opportunity type, location, work mode, contract, and salary."
          defaultOpen
          colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
        >
          <View style={styles.fieldBlock}>
            <Text style={[styles.fieldLabel, { color: textColor }]}>Opportunity types</Text>
            <PreferenceChipGroup
              options={ONBOARDING_OPPORTUNITY_TYPE_OPTIONS}
              value={editorState.opportunityTypes}
              onChange={(values) => setStateField('opportunityTypes', values)}
              colors={colors}
            />
          </View>

          <View style={styles.fieldBlock}>
            <Text style={[styles.fieldLabel, { color: textColor }]}>Preferred locations</Text>
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
              options={EMPLOYMENT_TYPE_OPTIONS}
              value={editorState.employmentTypes}
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

          <Field
            label="Maximum expected salary"
            value={editorState.formData.salaryMaxExpectation}
            onChangeText={(value) =>
              setFormField('salaryMaxExpectation', value.replace(/[^\d]/g, ''))
            }
            placeholder="Optional max"
            keyboardType="number-pad"
            error={fieldErrors.salaryRange}
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
          />
        </ProfileSection>

        <ProfileSection
          title="Career Signals"
          description="Roles, skills, and professional sectors."
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

        <ProfileSection
          title="Visibility"
          description="Control recruiter visibility without disabling recommendations."
          defaultOpen
          colors={{ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }}
        >
          <View
            style={[
              styles.visibilityCard,
              {
                borderColor: editorState.profileVisibility ? tintColor : borderColor,
                backgroundColor: editorState.profileVisibility ? `${tintColor}10` : cardColor,
              },
            ]}
          >
            <View style={styles.visibilityTextWrap}>
              <Text style={[styles.visibilityTitle, { color: textColor }]}>
                Hiring employers can find you
              </Text>
              <Text style={[styles.visibilityText, { color: mutedColor }]}>
                Make your profile visible to recruiters searching for candidates.
              </Text>
            </View>
            <Switch
              value={editorState.profileVisibility}
              onValueChange={(value) => setStateField('profileVisibility', value)}
              trackColor={{ false: borderColor, true: tintColor }}
              thumbColor="#ffffff"
            />
          </View>
        </ProfileSection>
      </ScrollView>

      <View
        style={[
          styles.saveBar,
          {
            backgroundColor: cardColor,
            borderColor,
            paddingBottom: Math.max(insets.bottom, 16),
          },
        ]}
      >
        <Pressable
          accessibilityRole="button"
          onPress={() => router.back()}
          style={[styles.secondaryButton, { borderColor }]}
        >
          <Text style={[styles.secondaryButtonText, { color: textColor }]}>Cancel</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={() => void handleSave()}
          disabled={saving || !isDirty}
          style={[
            styles.primaryButton,
            { backgroundColor: saving || !isDirty ? `${tintColor}55` : tintColor },
          ]}
        >
          <Text style={styles.primaryButtonText}>{saving ? 'Saving...' : 'Save changes'}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 16,
    paddingTop: 16,
    gap: 16,
  },
  headerBlock: {
    gap: 6,
  },
  title: {
    fontSize: 26,
    fontWeight: '800',
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 20,
  },
  feedbackCard: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    gap: 4,
  },
  feedbackTitle: {
    fontSize: 15,
    fontWeight: '800',
  },
  feedbackText: {
    fontSize: 13,
    lineHeight: 19,
  },
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
  fieldError: {
    color: '#dc2626',
    fontSize: 12,
    lineHeight: 17,
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
  visibilityCard: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  visibilityTextWrap: {
    flex: 1,
    gap: 4,
  },
  visibilityTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  visibilityText: {
    fontSize: 13,
    lineHeight: 18,
  },
  saveBar: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 10,
  },
  secondaryButton: {
    flex: 1,
    minHeight: 46,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  primaryButton: {
    flex: 1,
    minHeight: 46,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  centeredState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
    gap: 12,
  },
  stateTitle: {
    fontSize: 20,
    fontWeight: '800',
  },
  stateText: {
    fontSize: 14,
    lineHeight: 20,
    textAlign: 'center',
  },
  primaryInlineButton: {
    minHeight: 46,
    borderRadius: 12,
    paddingHorizontal: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryInlineButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
});
