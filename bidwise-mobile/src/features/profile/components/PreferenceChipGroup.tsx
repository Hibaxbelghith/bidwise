import { memo } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type Option = {
  value: string;
  label: string;
  description?: string;
};

type PreferenceChipGroupProps = {
  options: Option[];
  value: string[];
  onChange: (value: string[]) => void;
  colors: {
    tint: string;
    border: string;
    text: string;
    muted: string;
    card: string;
  };
  compact?: boolean;
};

function PreferenceChipGroup({
  options,
  value,
  onChange,
  colors,
  compact = false,
}: PreferenceChipGroupProps) {
  const selected = Array.isArray(value) ? value : [];

  return (
    <View style={styles.wrap}>
      {options.map((option) => {
        const active = selected.includes(option.value);
        return (
          <TouchableOpacity
            key={option.value}
            activeOpacity={0.75}
            onPress={() => {
              onChange(
                active
                  ? selected.filter((item) => item !== option.value)
                  : [...selected, option.value],
              );
            }}
            style={[
              compact ? styles.compactChip : styles.chip,
              {
                backgroundColor: active ? colors.tint : colors.card,
                borderColor: active ? colors.tint : colors.border,
              },
            ]}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
          >
            <Text style={[styles.label, { color: active ? '#fff' : colors.text }]}>{option.label}</Text>
            {!compact && option.description ? (
              <Text style={[styles.description, { color: active ? '#eef4ff' : colors.muted }]}>
                {option.description}
              </Text>
            ) : null}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

export default memo(PreferenceChipGroup);

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  chip: {
    borderWidth: 1.25,
    borderRadius: 12,
    flexBasis: '47%',
    flexGrow: 1,
    gap: 4,
    minHeight: 78,
    paddingHorizontal: 14,
    paddingVertical: 13,
  },
  compactChip: {
    borderWidth: 1.25,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  label: {
    fontSize: 14,
    fontWeight: '700',
  },
  description: {
    fontSize: 12,
    lineHeight: 16,
  },
});
