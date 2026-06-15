import { StyleSheet, Text, View } from 'react-native';

import type { StepDefinition } from '@/src/features/profile/onboarding/onboardingTypes';

type OnboardingProgressProps = {
  currentStep: number;
  steps: StepDefinition[];
  tint: string;
  border: string;
};

export default function OnboardingProgress({
  currentStep,
  steps,
  tint,
  border,
}: OnboardingProgressProps) {
  return (
    <>
      <View style={styles.progressContainer}>
        {steps.map((step, index) => (
          <View
            key={step.key}
            style={[
              styles.progressDot,
              { backgroundColor: index <= currentStep ? tint : border, flex: 1 },
            ]}
          />
        ))}
      </View>

      <Text style={[styles.stepLabel, { color: tint }]}>
        Step {currentStep + 1} of {steps.length}
      </Text>
    </>
  );
}

const styles = StyleSheet.create({
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
  stepLabel: {
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 8,
  },
});
