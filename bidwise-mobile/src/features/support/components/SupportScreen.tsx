import { Linking, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

const SUPPORT_EMAIL = 'support@bidwise.app';

export default function SupportScreen() {
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const openMail = () => {
    void Linking.openURL(`mailto:${SUPPORT_EMAIL}?subject=BidWise mobile support`);
  };

  return (
    <View style={styles.content}>
      <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
        <Text style={[styles.title, { color: textColor }]}>Need help?</Text>
        <Text style={[styles.body, { color: mutedColor }]}>
          Contact the BidWise support team if you have trouble signing in, completing your profile,
          or understanding how recommendations work.
        </Text>
        <TouchableOpacity
          accessibilityRole="button"
          activeOpacity={0.8}
          onPress={openMail}
          style={[styles.button, { backgroundColor: tintColor }]}
        >
          <Text style={styles.buttonText}>Contact support</Text>
        </TouchableOpacity>
        <Text style={[styles.email, { color: mutedColor }]}>{SUPPORT_EMAIL}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
    padding: 16,
  },
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    gap: 14,
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
  },
  body: {
    fontSize: 14,
    lineHeight: 21,
  },
  button: {
    minHeight: 46,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '800',
  },
  email: {
    fontSize: 13,
  },
});
