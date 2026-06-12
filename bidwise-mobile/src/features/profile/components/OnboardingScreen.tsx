import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';

import ProfileAutocompleteInput from '@/src/features/profile/components/ProfileAutocompleteInput';
import PreferenceChipGroup from '@/src/features/profile/components/PreferenceChipGroup';
import {
  DEFAULT_COMPENSATION_CURRENCY,
  DEFAULT_COMPENSATION_PERIOD,
  EMPLOYMENT_TYPE_OPTIONS,
  ONBOARDING_OPPORTUNITY_TYPE_OPTIONS,
  TUNISIAN_LOCATION_OPTIONS,
  WORK_MODE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';
import { useAuth } from '@/src/features/auth/context/AuthContext';
import { updateProfile } from '@/src/features/profile/services/profileService';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';
import {
  normalizeLocations,
  normalizeProfilePreferenceData,
  validateSalaryRange,
} from '@/src/features/profile/utils/profileValidation';

const STEPS = [
  { title: 'Opportunity goals', description: 'Choose what you want BidWise to prioritize.' },
  { title: 'Location and work mode', description: 'Location is required for on-site or hybrid work, and optional for remote.' },
  { title: 'Key skills', description: 'Skills power your AI match score.' },
  { title: 'Expected salary range', description: 'Optional TND/month range for less brittle matching.' },
  { title: 'Employment type', description: 'Select the contract types that fit your search.' },
  { title: 'Target roles', description: 'Roles must come from suggestions to protect matching quality.' },
  { title: 'Career interests', description: 'Industries and interests help tune recommendations.' },
  { title: 'Profile visibility', description: 'Control how recruiters see your profile.' },
];

const MAX_ROLES = 5;

type OnboardingData = {
  opportunity_types: string[];
  preferred_locations: string[];
  work_mode_preferences: string[];
  compensation_expectation: string;
  compensation_min_expectation: string;
  compensation_max_expectation: string;
  compensation_currency: string;
  compensation_period: string;
  employment_types: string[];
  target_roles: string[];
  competences: string[];
  domaines_interet: string[];
  profile_visibility: boolean;
};

const initialData: OnboardingData = {
  opportunity_types: [],
  preferred_locations: [],
  work_mode_preferences: [],
  compensation_expectation: '',
  compensation_min_expectation: '',
  compensation_max_expectation: '',
  compensation_currency: DEFAULT_COMPENSATION_CURRENCY,
  compensation_period: DEFAULT_COMPENSATION_PERIOD,
  employment_types: [],
  target_roles: [],
  competences: [],
  domaines_interet: [],
  profile_visibility: true,
};

export default function OnboardingScreen() {
  const router = useRouter();
  const { loadUserProfile } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [locationInput, setLocationInput] = useState('');
  const [data, setData] = useState<OnboardingData>(initialData);

  const bg = useThemeColor({}, 'background');
  const text = useThemeColor({}, 'text');
  const muted = useThemeColor({}, 'muted');
  const tint = useThemeColor({}, 'tint');
  const card = useThemeColor({}, 'card');
  const border = useThemeColor({}, 'border');
  const colors = useMemo(() => ({ tint, border, text, muted, card }), [border, card, muted, text, tint]);
  const isLast = currentStep === STEPS.length - 1;
  const step = STEPS[currentStep];

  const salaryRangeValidation = useMemo(
    () => validateSalaryRange(
      data.compensation_min_expectation,
      data.compensation_max_expectation,
      data.compensation_period,
    ),
    [data.compensation_min_expectation, data.compensation_max_expectation, data.compensation_period],
  );

  const addLocation = (location: string) => {
    const normalized = normalizeLocations([location])[0];
    if (!normalized) return;
    setData((prev) => ({
      ...prev,
      preferred_locations: normalizeLocations([...prev.preferred_locations, normalized]),
    }));
    setLocationInput('');
  };

  const removeLocation = (location: string) => {
    setData((prev) => ({
      ...prev,
      preferred_locations: prev.preferred_locations.filter((item) => item !== location),
    }));
  };

  const validateCurrentStep = () => {
    if (currentStep === 0 && data.opportunity_types.length === 0) return 'Select at least one opportunity type.';
    if (currentStep === 1 && data.work_mode_preferences.length === 0) return 'Select at least one work mode.';
    if (
      currentStep === 1 &&
      data.work_mode_preferences.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID') &&
      data.preferred_locations.length === 0
    ) {
      return 'Choose at least one location for on-site or hybrid work.';
    }
    if (currentStep === 2 && data.competences.length === 0) return 'Skills power your AI match score.';
    if (currentStep === 3 && salaryRangeValidation.error) return salaryRangeValidation.error;
    return '';
  };

  const handleNext = async () => {
    const validationError = validateCurrentStep();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError('');

    if (isLast) {
      await finishOnboarding(false);
    } else {
      setCurrentStep((value) => value + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) setCurrentStep((value) => value - 1);
  };

  const finishOnboarding = async (skipData: boolean) => {
    try {
      setSaving(true);
      setError('');
      const payload: Record<string, unknown> = {
        onboarding_completed: true,
        last_onboarding_step: currentStep,
      };

      if (!skipData) {
        Object.assign(payload, {
          ...normalizeProfilePreferenceData(data),
          compensation_expectation: salaryRangeValidation.min ?? salaryRangeValidation.max,
          compensation_min_expectation: salaryRangeValidation.min,
          compensation_max_expectation: salaryRangeValidation.max,
          compensation_currency: DEFAULT_COMPENSATION_CURRENCY,
          compensation_period: data.compensation_period || DEFAULT_COMPENSATION_PERIOD,
        });
      }

      await updateProfile(payload);
      await loadUserProfile();
      router.replace('/for-you');
    } catch {
      setError('Could not save your profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const renderLocationStep = () => (
    <View style={styles.stepBody}>
      <View style={styles.inputGroup}>
        <Text style={[styles.label, { color: text }]}>Preferred locations</Text>
        <View style={styles.inputRow}>
          <TextInput
            value={locationInput}
            onChangeText={setLocationInput}
            onSubmitEditing={() => addLocation(locationInput)}
            placeholder="Tunis, Sfax, Sousse..."
            placeholderTextColor={muted}
            style={[styles.input, { backgroundColor: card, borderColor: border, color: text }]}
          />
          <TouchableOpacity
            activeOpacity={0.75}
            onPress={() => addLocation(locationInput)}
            style={[styles.addButton, { backgroundColor: tint, opacity: locationInput.trim() ? 1 : 0.45 }]}
          >
            <Text style={styles.addText}>+</Text>
          </TouchableOpacity>
        </View>
      </View>
      <Text style={[styles.helperText, { color: muted }]}>
        {data.work_mode_preferences.some((mode) => mode === 'ON_SITE' || mode === 'HYBRID')
          ? 'Location is required for on-site or hybrid work.'
          : 'Location is optional when you are open to remote work.'}
      </Text>

      <View style={styles.quickWrap}>
        {TUNISIAN_LOCATION_OPTIONS.slice(0, 8).map((location) => (
          <TouchableOpacity
            key={location}
            activeOpacity={0.75}
            onPress={() => addLocation(location)}
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
              onPress={() => removeLocation(location)}
              style={[styles.selectedChip, { borderColor: tint, backgroundColor: tint + '18' }]}
            >
              <Text style={[styles.selectedText, { color: tint }]}>{location} ×</Text>
            </TouchableOpacity>
          ))}
        </View>
      ) : null}

      <View style={styles.inputGroup}>
        <Text style={[styles.label, { color: text }]}>Work modes</Text>
        <PreferenceChipGroup
          options={WORK_MODE_OPTIONS}
          value={data.work_mode_preferences}
          onChange={(value) => setData((prev) => ({ ...prev, work_mode_preferences: value }))}
          colors={colors}
          compact
        />
      </View>
    </View>
  );

  const toggleOpportunityType = (option: (typeof ONBOARDING_OPPORTUNITY_TYPE_OPTIONS)[number]) => {
    const selected = option.values.every((value) => data.opportunity_types.includes(value));
    setData((prev) => ({
      ...prev,
      opportunity_types: selected
        ? prev.opportunity_types.filter((value) => !option.values.includes(value))
        : Array.from(new Set([...prev.opportunity_types, ...option.values])),
    }));
  };

  const renderOpportunityStep = () => (
    <View style={styles.stepBody}>
      {ONBOARDING_OPPORTUNITY_TYPE_OPTIONS.map((option) => {
        const selected = option.values.every((value) => data.opportunity_types.includes(value));
        return (
          <TouchableOpacity
            key={option.value}
            activeOpacity={0.75}
            onPress={() => toggleOpportunityType(option)}
            style={[
              styles.optionCard,
              {
                borderColor: selected ? tint : border,
                backgroundColor: selected ? tint + '12' : card,
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

  const renderSalaryRangeStep = () => (
    <View style={styles.stepBody}>
      <Text style={[styles.label, { color: text }]}>Expected salary range</Text>
      <View style={styles.inputRow}>
        <TextInput
          value={data.compensation_min_expectation}
          onChangeText={(value) => setData((prev) => ({ ...prev, compensation_min_expectation: value }))}
          placeholder="Min"
          placeholderTextColor={muted}
          keyboardType="number-pad"
          style={[styles.input, { backgroundColor: card, borderColor: border, color: text }]}
        />
        <TextInput
          value={data.compensation_max_expectation}
          onChangeText={(value) => setData((prev) => ({ ...prev, compensation_max_expectation: value }))}
          placeholder="Max"
          placeholderTextColor={muted}
          keyboardType="number-pad"
          style={[styles.input, { backgroundColor: card, borderColor: border, color: text }]}
        />
      </View>
      <Text style={[styles.helperText, { color: muted }]}>TND/month. Optional.</Text>
    </View>
  );

  const stepRenderers = [
    renderOpportunityStep,
    renderLocationStep,
    () => (
      <ProfileAutocompleteInput
        label="What are your top skills?"
        termType="skill"
        value={data.competences}
        onChange={(value) => setData((prev) => ({ ...prev, competences: value }))}
        placeholder="Python, React, Django..."
        colors={colors}
      />
    ),
    renderSalaryRangeStep,
    () => (
      <PreferenceChipGroup
        options={EMPLOYMENT_TYPE_OPTIONS}
        value={data.employment_types}
        onChange={(value) => setData((prev) => ({ ...prev, employment_types: value }))}
        colors={colors}
        compact
      />
    ),
    () => (
      <ProfileAutocompleteInput
        label="Target roles"
        termType="role"
        value={data.target_roles}
        onChange={(value) => setData((prev) => ({ ...prev, target_roles: value }))}
        placeholder="Frontend Developer, Backend Developer..."
        maxItems={MAX_ROLES}
        colors={colors}
      />
    ),
    () => (
      <View style={styles.stepBody}>
        <ProfileAutocompleteInput
          label="Industries / Interests"
          termType="interest"
          value={data.domaines_interet}
          onChange={(value) => setData((prev) => ({ ...prev, domaines_interet: value }))}
          placeholder="Healthcare, Fintech, AI..."
          maxItems={8}
          colors={colors}
        />
      </View>
    ),
    () => (
      <TouchableOpacity
        activeOpacity={0.8}
        onPress={() => setData((prev) => ({ ...prev, profile_visibility: !prev.profile_visibility }))}
        style={[
          styles.visibilityCard,
          {
            borderColor: data.profile_visibility ? tint : border,
            backgroundColor: data.profile_visibility ? tint + '10' : card,
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
          onValueChange={(value) => setData((prev) => ({ ...prev, profile_visibility: value }))}
          trackColor={{ false: border, true: tint }}
          thumbColor="#fff"
        />
      </TouchableOpacity>
    ),
  ];

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: bg }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.progressContainer}>
        {STEPS.map((item, index) => (
          <View
            key={item.title}
            style={[
              styles.progressDot,
              { backgroundColor: index <= currentStep ? tint : border, flex: 1 },
            ]}
          />
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={[styles.stepLabel, { color: tint }]}>Step {currentStep + 1} of {STEPS.length}</Text>
        <Text style={[styles.title, { color: text }]}>{step.title}</Text>
        <Text style={[styles.subtitle, { color: muted }]}>{step.description}</Text>
        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={styles.stepCard}>{stepRenderers[currentStep]()}</View>
      </ScrollView>

      <View style={[styles.footer, { backgroundColor: bg, borderTopColor: border }]}>
        {saving ? <ActivityIndicator color={tint} style={styles.saving} /> : null}
        <View style={styles.footerRow}>
          {currentStep > 0 ? (
            <TouchableOpacity style={[styles.secondaryButton, { borderColor: border }]} onPress={handleBack} activeOpacity={0.75}>
              <Text style={[styles.secondaryButtonText, { color: text }]}>Back</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity onPress={() => finishOnboarding(true)} activeOpacity={0.75} disabled={saving}>
              <Text style={[styles.skipText, { color: muted }]}>Skip</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={[styles.primaryButton, { backgroundColor: tint, opacity: saving ? 0.6 : 1 }]}
            onPress={handleNext}
            activeOpacity={0.8}
            disabled={saving}
          >
            <Text style={styles.primaryButtonText}>{isLast ? 'Finish' : 'Next'}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 58,
  },
  progressContainer: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 26,
    paddingHorizontal: 24,
  },
  progressDot: {
    borderRadius: 2,
    height: 4,
  },
  scrollContent: {
    flexGrow: 1,
    paddingBottom: 32,
    paddingHorizontal: 24,
  },
  stepLabel: {
    fontSize: 13,
    fontWeight: '800',
    marginBottom: 8,
  },
  title: {
    fontSize: 26,
    fontWeight: '800',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    lineHeight: 22,
    marginBottom: 22,
  },
  stepCard: {
    gap: 16,
  },
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
    fontWeight: '800',
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
    fontWeight: '800',
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
    fontWeight: '800',
  },
  visibilityDesc: {
    fontSize: 13,
    lineHeight: 18,
  },
  errorText: {
    color: '#dc2626',
    fontSize: 13,
    marginBottom: 12,
  },
  footer: {
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingBottom: 30,
    paddingHorizontal: 24,
    paddingTop: 14,
  },
  saving: {
    marginBottom: 10,
  },
  footerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  secondaryButton: {
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 24,
    paddingVertical: 12,
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: '700',
  },
  primaryButton: {
    borderRadius: 12,
    paddingHorizontal: 32,
    paddingVertical: 12,
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '800',
  },
  skipText: {
    fontSize: 15,
    fontWeight: '700',
  },
});
