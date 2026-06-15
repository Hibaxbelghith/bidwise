import { StyleSheet, Text, TextInput, View } from 'react-native';

type ProfileFormFieldProps = {
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
};

export default function ProfileFormField({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType = 'default',
  error,
  textColor,
  mutedColor,
  borderColor,
  cardColor,
}: ProfileFormFieldProps) {
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
  fieldError: {
    color: '#dc2626',
    fontSize: 12,
    lineHeight: 17,
  },
});
