import { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import OnboardingFooter from '@/src/features/profile/components/onboarding/OnboardingFooter';
import OnboardingProgress from '@/src/features/profile/components/onboarding/OnboardingProgress';
import OnboardingStepContent from '@/src/features/profile/components/onboarding/OnboardingStepContent';
import { ONBOARDING_OPPORTUNITY_TYPE_OPTIONS } from '@/src/features/profile/constants/profileOptions';
import {
  INITIAL_ONBOARDING_DATA,
  STEP_DEFINITIONS,
} from '@/src/features/profile/onboarding/onboardingConfig';
import {
  buildOnboardingDataFromProfile,
  resolveOnboardingStepFromProfile,
} from '@/src/features/profile/onboarding/onboardingState';
import type { OnboardingData } from '@/src/features/profile/onboarding/onboardingTypes';
import {
  getOnboardingStepError,
  MAX_ONBOARDING_LOCATIONS,
} from '@/src/features/profile/onboarding/onboardingValidation';
import {
  getProfile,
  getProfileUpdateErrorMessage,
  updateProfile,
} from '@/src/features/profile/services/profileService';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';
import {
  normalizeLocations,
  normalizeProfilePreferenceData,
  validateSalaryRange,
} from '@/src/features/profile/utils/profileValidation';

export default function OnboardingScreen() {
  const router = useRouter();
  const { loadUserProfile } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [error, setError] = useState('');
  const [locationInput, setLocationInput] = useState('');
  const [data, setData] = useState<OnboardingData>(INITIAL_ONBOARDING_DATA);

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

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

  const isLast = currentStep === STEP_DEFINITIONS.length - 1;
  const step = STEP_DEFINITIONS[currentStep];

  useEffect(() => {
    let cancelled = false;

    const loadOnboardingState = async () => {
      try {
        setLoadingProfile(true);
        const profileResponse = await getProfile();
        const profile = profileResponse?.profil ?? null;

        if (cancelled) return;

        if (profile?.onboarding_completed) {
          router.replace('/explore');
          return;
        }

        setData(buildOnboardingDataFromProfile(profile));
        setCurrentStep(resolveOnboardingStepFromProfile(profile));
      } catch {
        if (!cancelled) {
          setCurrentStep(0);
          setData(INITIAL_ONBOARDING_DATA);
        }
      } finally {
        if (!cancelled) {
          setLoadingProfile(false);
        }
      }
    };

    void loadOnboardingState();

    return () => {
      cancelled = true;
    };
  }, [router]);

  const salaryRangeValidation = useMemo(
    () =>
      validateSalaryRange(
        data.compensation_min_expectation,
        data.compensation_max_expectation,
        data.compensation_period,
      ),
    [
      data.compensation_min_expectation,
      data.compensation_max_expectation,
      data.compensation_period,
    ],
  );

  const updateField = <K extends keyof OnboardingData>(field: K, value: OnboardingData[K]) => {
    setData((prev) => ({ ...prev, [field]: value }));
  };

  const addLocation = (location: string) => {
    const normalized = normalizeLocations([location])[0];
    if (!normalized) return;

    const alreadySelected = data.preferred_locations.some(
      (item) => item.toLowerCase() === normalized.toLowerCase(),
    );
    if (alreadySelected) {
      setLocationInput('');
      setError('');
      return;
    }

    if (data.preferred_locations.length >= MAX_ONBOARDING_LOCATIONS) {
      setError(`You can add up to ${MAX_ONBOARDING_LOCATIONS} locations.`);
      return;
    }

    setData((prev) => ({
      ...prev,
      preferred_locations: normalizeLocations([...prev.preferred_locations, normalized]),
    }));
    setLocationInput('');
    setError('');
  };

  const removeLocation = (location: string) => {
    setData((prev) => ({
      ...prev,
      preferred_locations: prev.preferred_locations.filter((item) => item !== location),
    }));
    setError('');
  };

  const toggleOpportunityType = (
    option: (typeof ONBOARDING_OPPORTUNITY_TYPE_OPTIONS)[number],
  ) => {
    const selected = option.values.every((value) => data.opportunity_types.includes(value));

    setData((prev) => ({
      ...prev,
      opportunity_types: selected
        ? prev.opportunity_types.filter((value) => !option.values.includes(value))
        : Array.from(new Set([...prev.opportunity_types, ...option.values])),
    }));
  };

  const validateCurrentStep = () =>
    getOnboardingStepError({
      stepKey: step.key,
      data,
      salaryError: salaryRangeValidation.error,
    });

  const buildOnboardingPayload = ({
    onboardingCompleted,
    stepIndex,
  }: {
    onboardingCompleted: boolean;
    stepIndex: number;
  }) => {
    const normalized = {
      ...normalizeProfilePreferenceData(data),
      compensation_expectation: salaryRangeValidation.min ?? salaryRangeValidation.max,
      compensation_min_expectation: salaryRangeValidation.min,
      compensation_max_expectation: salaryRangeValidation.max,
      compensation_currency: data.compensation_currency,
      compensation_period: data.compensation_period,
      onboarding_completed: onboardingCompleted,
      last_onboarding_step: stepIndex,
    };

    return Object.fromEntries(
      Object.entries(normalized).filter(([, value]) => {
        if (Array.isArray(value)) return value.length > 0;
        if (value === '' || value == null) return false;
        return true;
      }),
    );
  };

  const persistOnboardingProgress = async ({
    onboardingCompleted,
    stepIndex,
  }: {
    onboardingCompleted: boolean;
    stepIndex: number;
  }) => {
    await updateProfile(
      buildOnboardingPayload({
        onboardingCompleted,
        stepIndex,
      }),
    );
  };

  const finishOnboarding = async () => {
    try {
      setSaving(true);
      setError('');

      await persistOnboardingProgress({
        onboardingCompleted: true,
        stepIndex: currentStep,
      });
      await loadUserProfile();
      router.replace('/explore');
    } catch (errorResponse) {
      setError(
        getProfileUpdateErrorMessage(
          errorResponse,
          'Could not save your profile. Please try again.',
        ),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleSkip = async () => {
    try {
      setSaving(true);
      setError('');

      await persistOnboardingProgress({
        onboardingCompleted: false,
        stepIndex: currentStep,
      });
      await loadUserProfile();
      router.replace('/explore');
    } catch (errorResponse) {
      setError(
        getProfileUpdateErrorMessage(
          errorResponse,
          'Could not save your profile. Please try again.',
        ),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleNext = async () => {
    if (loadingProfile) return;

    const validationError = validateCurrentStep();
    if (validationError) {
      setError(validationError);
      return;
    }

    setError('');

    if (isLast) {
      await finishOnboarding();
      return;
    }

    const nextStep = currentStep + 1;

    try {
      setSaving(true);
      await persistOnboardingProgress({
        onboardingCompleted: false,
        stepIndex: nextStep,
      });
      setCurrentStep(nextStep);
    } catch (errorResponse) {
      setError(
        getProfileUpdateErrorMessage(
          errorResponse,
          'Could not save your progress. Please try again.',
        ),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    if (loadingProfile) return;

    if (currentStep > 0) {
      setCurrentStep((value) => value - 1);
    }
  };

  if (loadingProfile) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor }]}>
        <ActivityIndicator size="large" color={tintColor} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <OnboardingProgress
        currentStep={currentStep}
        steps={STEP_DEFINITIONS}
        tint={tintColor}
        border={borderColor}
      />

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={[styles.title, { color: textColor }]}>{step.title}</Text>
        <Text style={[styles.subtitle, { color: mutedColor }]}>{step.description}</Text>
        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={styles.stepCard}>
          <OnboardingStepContent
            stepKey={step.key}
            data={data}
            locationInput={locationInput}
            onLocationInputChange={setLocationInput}
            onAddLocation={addLocation}
            onRemoveLocation={removeLocation}
            onToggleOpportunityType={toggleOpportunityType}
            onUpdateField={updateField}
            colors={colors}
          />
        </View>
      </ScrollView>

      <OnboardingFooter
        backgroundColor={backgroundColor}
        borderColor={borderColor}
        textColor={textColor}
        mutedColor={mutedColor}
        tintColor={tintColor}
        currentStep={currentStep}
        isLast={isLast}
        saving={saving}
        onBack={handleBack}
        onSkip={handleSkip}
        onNext={handleNext}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 58,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scrollContent: {
    flexGrow: 1,
    paddingBottom: 32,
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
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
  errorText: {
    color: '#dc2626',
    fontSize: 13,
    marginBottom: 12,
  },
});
