import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type OnboardingFooterProps = {
  backgroundColor: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
  currentStep: number;
  isLast: boolean;
  saving: boolean;
  onBack: () => void;
  onSkip: () => void;
  onNext: () => void;
};

export default function OnboardingFooter({
  backgroundColor,
  borderColor,
  textColor,
  mutedColor,
  tintColor,
  currentStep,
  isLast,
  saving,
  onBack,
  onSkip,
  onNext,
}: OnboardingFooterProps) {
  return (
    <View style={[styles.footer, { backgroundColor, borderTopColor: borderColor }]}>
      {saving ? <ActivityIndicator color={tintColor} style={styles.saving} /> : null}

      <View style={styles.footerRow}>
        {currentStep > 0 ? (
          <TouchableOpacity
            style={[styles.secondaryButton, { borderColor }]}
            onPress={onBack}
            activeOpacity={0.75}
          >
            <Text style={[styles.secondaryButtonText, { color: textColor }]}>Back</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity onPress={onSkip} activeOpacity={0.75} disabled={saving}>
            <Text style={[styles.skipText, { color: mutedColor }]}>Skip</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[styles.primaryButton, { backgroundColor: tintColor, opacity: saving ? 0.6 : 1 }]}
          onPress={onNext}
          activeOpacity={0.8}
          disabled={saving}
        >
          <Text style={styles.primaryButtonText}>{isLast ? 'Finish' : 'Next'}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
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
    fontWeight: '700',
  },
  skipText: {
    fontSize: 15,
    fontWeight: '700',
  },
});
