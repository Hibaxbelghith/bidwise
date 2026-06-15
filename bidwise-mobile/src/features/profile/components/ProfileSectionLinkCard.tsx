import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

type ProfileSectionLinkCardProps = {
  title: string;
  description: string;
  summary: string;
  onPress: () => void;
};

export default function ProfileSectionLinkCard({
  title,
  description,
  summary,
  onPress,
}: ProfileSectionLinkCardProps) {
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: cardColor,
          borderColor,
          opacity: pressed ? 0.94 : 1,
        },
      ]}
    >
      <View style={styles.textWrap}>
        <Text style={[styles.title, { color: textColor }]}>{title}</Text>
        <Text style={[styles.description, { color: mutedColor }]}>{description}</Text>
        <Text style={[styles.summary, { color: tintColor }]} numberOfLines={2}>
          {summary}
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={mutedColor} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 18,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 16,
  },
  textWrap: {
    flex: 1,
    gap: 4,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
  },
  description: {
    fontSize: 13,
    lineHeight: 18,
  },
  summary: {
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 18,
    marginTop: 2,
  },
});
