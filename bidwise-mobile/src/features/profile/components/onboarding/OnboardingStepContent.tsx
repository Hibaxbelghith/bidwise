import { StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from 'react-native';

import ProfileAutocompleteInput from '@/src/features/profile/components/ProfileAutocompleteInput';
import PreferenceChipGroup from '@/src/features/profile/components/PreferenceChipGroup';
import {
  BUSINESS_FAMILY_OPTIONS,
  getEmploymentTypeOptionsForOpportunityTypes,
  ONBOARDING_OPPORTUNITY_TYPE_OPTIONS,
  TUNISIAN_LOCATION_OPTIONS,
  WORK_MODE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';
import { MAX_ROLES } from '@/src/features/profile/onboarding/onboardingConfig';
import type {
  OnboardingData,
  OnboardingThemeColors,
  StepKey,
} from '@/src/features/profile/onboarding/onboardingTypes';

type OnboardingStepContentProps = {
  stepKey: StepKey;
  data: OnboardingData;
  locationInput: string;
  onLocationInputChange: (value: string) => void;
  onAddLocation: (location: string) => void;
  onRemoveLocation: (location: string) => void;
  onToggleOpportunityType: (
    option: (typeof ONBOARDING_OPPORTUNITY_TYPE_OPTIONS)[number],
  ) => void;
  onUpdateField: <K extends keyof OnboardingData>(field: K, value: OnboardingData[K]) => void;
  colors: OnboardingThemeColors;
};

function OpportunityIntentStep({
  data,
  onToggleOpportunityType,
  colors,
}: Pick<OnboardingStepContentProps, 'data' | 'onToggleOpportunityType' | 'colors'>) {
  const { tint, border, text, muted, card } = colors;

  return (
    <View style={styles.stepBody}>
      {ONBOARDING_OPPORTUNITY_TYPE_OPTIONS.map((option) => {
        const selected = option.values.every((value) => data.opportunity_types.includes(value));

        return (
          <TouchableOpacity
            key={option.value}
            activeOpacity={0.75}
            onPress={() => onToggleOpportunityType(option)}
            style={[
              styles.optionCard,
              {
                borderColor: selected ? tint : border,
                backgroundColor: selected ? `${tint}12` : card,
              },
            ]}
          >
            <Text style={[styles.optionTitle, { color: selected ? tint : text }]}>{option.label}</Text>
            <Text style={[styles.optionDescription, { color: muted }]}>{option.description}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function LocationStep({
  data,
  locationInput,
  onLocationInputChange,
  onAddLocation,
  onRemoveLocation,
  onUpdateField,
  colors,
}: Pick<
  OnboardingStepContentProps,
  | 'data'
  | 'locationInput'
  | 'onLocationInputChange'
  | 'onAddLocation'
  | 'onRemoveLocation'
  | 'onUpdateField'
  | 'colors'
>) {
  const { tint, border, text, muted, card } = colors;
  const requiresLocation = data.work_mode_preferences.some(
    (mode) => mode === 'ON_SITE' || mode === 'HYBRID',
  );
  const normalizedQuery = locationInput.trim().toLowerCase();
  const selectedKeys = new Set(data.preferred_locations.map((item) => item.toLowerCase()));
  const filteredSuggestions = TUNISIAN_LOCATION_OPTIONS.filter((location) => {
    if (selectedKeys.has(location.toLowerCase())) return false;
    if (!normalizedQuery) return true;
    return location.toLowerCase().includes(normalizedQuery);
  }).slice(0, 6);

  return (
    <View style={styles.stepBody}>
      <View style={styles.inputGroup}>
        <Text style={[styles.label, { color: text }]}>Preferred locations</Text>
        <View style={styles.inputRow}>
          <TextInput
            value={locationInput}
            onChangeText={onLocationInputChange}
            onSubmitEditing={() => onAddLocation(locationInput)}
            placeholder="Tunis, Sfax, Sousse..."
            placeholderTextColor={muted}
            style={[styles.input, { backgroundColor: card, borderColor: border, color: text }]}
          />
          <TouchableOpacity
            activeOpacity={0.75}
            onPress={() => onAddLocation(locationInput)}
            style={[
              styles.addButton,
              { backgroundColor: tint, opacity: locationInput.trim() ? 1 : 0.45 },
            ]}
          >
            <Text style={styles.addText}>+</Text>
          </TouchableOpacity>
        </View>
      </View>

      <Text style={[styles.helperText, { color: muted }]}>
        {requiresLocation
          ? 'Location is required for on-site or hybrid work.'
          : 'Location is optional when you are open to remote work.'}
      </Text>

      <View style={styles.quickWrap}>
        {filteredSuggestions.map((location) => (
          <TouchableOpacity
            key={location}
            activeOpacity={0.75}
            onPress={() => onAddLocation(location)}
            style={[styles.quickChip, { borderColor: border, backgroundColor: card }]}
          >
            <Text style={[styles.quickText, { color: text }]}>{location}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {data.preferred_locations.length ? (
        <View style={styles.selectedWrap}>
          {data.preferred_locations.map((location) => (
            <TouchableOpacity
              key={location}
              activeOpacity={0.75}
              onPress={() => onRemoveLocation(location)}
              style={[styles.selectedChip, { borderColor: tint, backgroundColor: `${tint}18` }]}
            >
              <Text style={[styles.selectedText, { color: tint }]}>{location} x</Text>
            </TouchableOpacity>
          ))}
        </View>
      ) : null}

      <View style={styles.inputGroup}>
        <Text style={[styles.label, { color: text }]}>Work modes</Text>
        <PreferenceChipGroup
          options={WORK_MODE_OPTIONS}
          value={data.work_mode_preferences}
          onChange={(value) => onUpdateField('work_mode_preferences', value)}
          colors={colors}
          compact
        />
      </View>
    </View>
  );
}

function SalaryStep({
  data,
  onUpdateField,
  colors,
}: Pick<OnboardingStepContentProps, 'data' | 'onUpdateField' | 'colors'>) {
  const { border, text, muted, card } = colors;

  return (
    <View style={styles.stepBody}>
      <Text style={[styles.label, { color: text }]}>Expected salary range</Text>
      <View style={styles.inputRow}>
        <TextInput
          value={data.compensation_min_expectation}
          onChangeText={(value) => onUpdateField('compensation_min_expectation', value)}
          placeholder="Min"
          placeholderTextColor={muted}
          keyboardType="number-pad"
          style={[styles.input, { backgroundColor: card, borderColor: border, color: text }]}
        />
        <TextInput
          value={data.compensation_max_expectation}
          onChangeText={(value) => onUpdateField('compensation_max_expectation', value)}
          placeholder="Max"
          placeholderTextColor={muted}
          keyboardType="number-pad"
          style={[styles.input, { backgroundColor: card, borderColor: border, color: text }]}
        />
      </View>
      <Text style={[styles.helperText, { color: muted }]}>TND/month. Optional.</Text>
    </View>
  );
}

function VisibilityStep({
  data,
  onUpdateField,
  colors,
}: Pick<OnboardingStepContentProps, 'data' | 'onUpdateField' | 'colors'>) {
  const { tint, border, text, muted, card } = colors;

  return (
    <TouchableOpacity
      activeOpacity={0.8}
      onPress={() => onUpdateField('profile_visibility', !data.profile_visibility)}
      style={[
        styles.visibilityCard,
        {
          borderColor: data.profile_visibility ? tint : border,
          backgroundColor: data.profile_visibility ? `${tint}10` : card,
        },
      ]}
    >
      <View style={styles.visibilityText}>
        <Text style={[styles.visibilityTitle, { color: text }]}>Profile visible to recruiters</Text>
        <Text style={[styles.visibilityDesc, { color: muted }]}>
          You can hide your profile while keeping recommendations active.
        </Text>
      </View>
      <Switch
        value={data.profile_visibility}
        onValueChange={(value) => onUpdateField('profile_visibility', value)}
        trackColor={{ false: border, true: tint }}
        thumbColor="#fff"
      />
    </TouchableOpacity>
  );
}

export default function OnboardingStepContent({
  stepKey,
  data,
  locationInput,
  onLocationInputChange,
  onAddLocation,
  onRemoveLocation,
  onToggleOpportunityType,
  onUpdateField,
  colors,
}: OnboardingStepContentProps) {
  switch (stepKey) {
    case 'opportunity_intent':
      return (
        <OpportunityIntentStep
          data={data}
          onToggleOpportunityType={onToggleOpportunityType}
          colors={colors}
        />
      );
    case 'location':
      return (
        <LocationStep
          data={data}
          locationInput={locationInput}
          onLocationInputChange={onLocationInputChange}
          onAddLocation={onAddLocation}
          onRemoveLocation={onRemoveLocation}
          onUpdateField={onUpdateField}
          colors={colors}
        />
      );
    case 'skills':
      return (
        <ProfileAutocompleteInput
          label="What are your top skills?"
          termType="skill"
          value={data.competences}
          onChange={(value) => onUpdateField('competences', value)}
          placeholder="Python, React, Django..."
          colors={colors}
        />
      );
    case 'sectors_interests':
      return (
        <View style={styles.stepBody}>
          <Text style={[styles.label, { color: colors.text }]}>Sectors</Text>
          <Text style={[styles.helperText, { color: colors.muted }]}>
            Choose up to 5 professional domains used by the AI matching engine.
          </Text>
          <PreferenceChipGroup
            options={BUSINESS_FAMILY_OPTIONS}
            value={data.domaines_interet}
            onChange={(value) => onUpdateField('domaines_interet', value.slice(0, 5))}
            colors={colors}
            compact
          />
        </View>
      );
    case 'salary':
      return <SalaryStep data={data} onUpdateField={onUpdateField} colors={colors} />;
    case 'employment_type': {
      const employmentTypeOptions = getEmploymentTypeOptionsForOpportunityTypes(data.opportunity_types);
      const visibleEmploymentTypeValues = new Set(
        employmentTypeOptions.map((option) => option.value),
      );
      return (
        <PreferenceChipGroup
          options={employmentTypeOptions}
          value={data.employment_types.filter((value) => visibleEmploymentTypeValues.has(value))}
          onChange={(value) => onUpdateField('employment_types', value)}
          colors={colors}
          compact
        />
      );
    }
    case 'target_roles':
      return (
        <ProfileAutocompleteInput
          label="Target roles"
          termType="role"
          value={data.target_roles}
          onChange={(value) => onUpdateField('target_roles', value)}
          placeholder="Frontend Developer, Backend Developer..."
          maxItems={MAX_ROLES}
          colors={colors}
        />
      );
    case 'visibility':
      return <VisibilityStep data={data} onUpdateField={onUpdateField} colors={colors} />;
    default:
      return null;
  }
}

const styles = StyleSheet.create({
  stepBody: {
    gap: 18,
  },
  inputGroup: {
    gap: 10,
  },
  label: {
    fontSize: 15,
    fontWeight: '700',
  },
  helperText: {
    fontSize: 13,
    lineHeight: 18,
  },
  optionCard: {
    borderRadius: 16,
    borderWidth: 1.25,
    padding: 16,
  },
  optionTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 4,
  },
  optionDescription: {
    fontSize: 13,
    lineHeight: 18,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 8,
  },
  input: {
    borderRadius: 12,
    borderWidth: 1,
    flex: 1,
    fontSize: 15,
    paddingHorizontal: 14,
    paddingVertical: 11,
  },
  addButton: {
    alignItems: 'center',
    borderRadius: 12,
    height: 46,
    justifyContent: 'center',
    width: 46,
  },
  addText: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '700',
  },
  quickWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  quickChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  quickText: {
    fontSize: 13,
    fontWeight: '600',
  },
  selectedWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  selectedChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  selectedText: {
    fontSize: 13,
    fontWeight: '700',
  },
  visibilityCard: {
    alignItems: 'center',
    borderRadius: 16,
    borderWidth: 1.25,
    flexDirection: 'row',
    gap: 16,
    padding: 18,
  },
  visibilityText: {
    flex: 1,
    gap: 4,
  },
  visibilityTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  visibilityDesc: {
    fontSize: 13,
    lineHeight: 18,
  },
});
