import { memo } from 'react';
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

import {
  COMPENSATION_PERIOD_OPTIONS,
  DEFAULT_COMPENSATION_PERIOD,
} from '@/src/features/profile/constants/profileOptions';
import { validateSalaryExpectation } from '@/src/features/profile/utils/profileValidation';

type SalaryExpectationFieldProps = {
  amount: string;
  period: string | null;
  onAmountChange: (value: string) => void;
  onPeriodChange: (value: string) => void;
  colors: {
    tint: string;
    border: string;
    text: string;
    muted: string;
    card: string;
  };
};

function SalaryExpectationField({
  amount,
  period,
  onAmountChange,
  onPeriodChange,
  colors,
}: SalaryExpectationFieldProps) {
  const selectedPeriod = period || DEFAULT_COMPENSATION_PERIOD;
  const validation = validateSalaryExpectation(amount, selectedPeriod);

  return (
    <View style={styles.container}>
      <View style={styles.labelRow}>
        <Text style={[styles.label, { color: colors.text }]}>Expected salary (TND / month)</Text>
        <Text style={[styles.currency, { color: colors.tint }]}>TND</Text>
      </View>

      <TextInput
        value={amount}
        onChangeText={(value) => onAmountChange(value.replace(/[^\d-]/g, ''))}
        placeholder="1800"
        placeholderTextColor={colors.muted}
        keyboardType="number-pad"
        inputMode="numeric"
        style={[
          styles.input,
          {
            backgroundColor: colors.card,
            borderColor: validation.error ? '#dc2626' : colors.border,
            color: colors.text,
          },
        ]}
      />

      <View style={styles.periodRow}>
        {COMPENSATION_PERIOD_OPTIONS.map((option) => {
          const active = selectedPeriod === option.value;
          return (
            <TouchableOpacity
              key={option.value}
              activeOpacity={0.75}
              onPress={() => onPeriodChange(option.value)}
              style={[
                styles.periodChip,
                {
                  backgroundColor: active ? colors.tint : colors.card,
                  borderColor: active ? colors.tint : colors.border,
                },
              ]}
            >
              <Text style={[styles.periodLabel, { color: active ? '#fff' : colors.text }]}>{option.label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <Text style={[styles.helper, { color: validation.error ? '#dc2626' : colors.muted }]}>
        {validation.error || 'Use a realistic Tunisian monthly expectation. Monthly is selected by default.'}
      </Text>
    </View>
  );
}

export default memo(SalaryExpectationField);

const styles = StyleSheet.create({
  container: {
    gap: 10,
  },
  labelRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  label: {
    fontSize: 15,
    fontWeight: '700',
  },
  currency: {
    fontSize: 12,
    fontWeight: '800',
  },
  input: {
    borderRadius: 12,
    borderWidth: 1,
    fontSize: 18,
    fontWeight: '700',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  periodRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  periodChip: {
    borderRadius: 999,
    borderWidth: 1.25,
    paddingHorizontal: 13,
    paddingVertical: 8,
  },
  periodLabel: {
    fontSize: 13,
    fontWeight: '700',
  },
  helper: {
    fontSize: 12,
    lineHeight: 17,
  },
});
