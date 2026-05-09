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
import SalaryExpectationField from '@/src/features/profile/components/SalaryExpectationField';
import {
  DEFAULT_COMPENSATION_CURRENCY,
  DEFAULT_COMPENSATION_PERIOD,
  EMPLOYMENT_TYPE_OPTIONS,
  OPPORTUNITY_TYPE_OPTIONS,
  TUNISIAN_LOCATION_OPTIONS,
  WORK_MODE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';
import { useAuth } from '@/src/features/auth/context/AuthContext';
import { updateProfile } from '@/src/features/profile/services/profileService';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';
import {
  normalizeLocations,
  normalizeProfilePreferenceData,
  validateSalaryExpectation,
} from '@/src/features/profile/utils/profileValidation';

const STEPS = [
  { title: 'Opportunity goals', description: 'Choose what you want BidWise to prioritize.' },
  { title: 'Location and work mode', description: 'Keep this Tunisia-first, with custom values when needed.' },
  { title: 'Expected salary', description: 'Tunisia market defaults to TND per month.' },
  { title: 'Employment type', description: 'Select the contract types that fit your search.' },
  { title: 'Target roles', description: 'Roles must come from suggestions to protect matching quality.' },
  { title: 'Career signals', description: 'Skills are what you can do. Interests are industries you want.' },
  { title: 'Profile visibility', description: 'Control how recruiters see your profile.' },
];

const MAX_ROLES = 5;

type OnboardingData = {
  opportunity_types: string[];
  preferred_locations: string[];
  work_mode_preferences: string[];
  compensation_expectation: string;
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

  const salaryValidation = useMemo(
    () => validateSalaryExpectation(data.compensation_expectation, data.compensation_period),
    [data.compensation_expectation, data.compensation_period],
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
    if (currentStep === 2 && salaryValidation.error) return salaryValidation.error;
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
          compensation_expectation: salaryValidation.value,
          compensation_currency: DEFAULT_COMPENSATION_CURRENCY,
          compensation_period: data.compensation_period || DEFAULT_COMPENSATION_PERIOD,
        });
      }

      await updateProfile(payload);
      await loadUserProfile();
      router.replace('/dashboard');
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

  const stepRenderers = [
    () => (
      <PreferenceChipGroup
        options={OPPORTUNITY_TYPE_OPTIONS}
        value={data.opportunity_types}
        onChange={(value) => setData((prev) => ({ ...prev, opportunity_types: value }))}
        colors={colors}
      />
    ),
    renderLocationStep,
    () => (
      <SalaryExpectationField
        amount={data.compensation_expectation}
        period={data.compensation_period}
        onAmountChange={(value) => setData((prev) => ({ ...prev, compensation_expectation: value }))}
        onPeriodChange={(value) => setData((prev) => ({ ...prev, compensation_period: value }))}
        colors={colors}
      />
    ),
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
          label="Skills"
          termType="skill"
          value={data.competences}
          onChange={(value) => setData((prev) => ({ ...prev, competences: value }))}
          placeholder="React, Python, CSS..."
          colors={colors}
        />
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
