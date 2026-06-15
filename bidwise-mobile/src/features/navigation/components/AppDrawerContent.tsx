import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type DrawerAction = {
  key: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  danger?: boolean;
};

type AppDrawerContentProps = {
  name: string;
  email: string;
  backgroundColor: string;
  borderColor: string;
  cardColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
  actions: DrawerAction[];
};

function getInitials(name: string, email: string) {
  const base = String(name || '').trim() || String(email || '').trim() || 'BW';
  const parts = base.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0]?.[0] || ''}${parts[1]?.[0] || ''}`.toUpperCase();
}

export default function AppDrawerContent({
  name,
  email,
  backgroundColor,
  borderColor,
  cardColor,
  textColor,
  mutedColor,
  tintColor,
  actions,
}: AppDrawerContentProps) {
  return (
    <View style={[styles.drawer, { backgroundColor, borderColor }]}>
      <View style={styles.profileCard}>
        <View style={[styles.avatar, { backgroundColor: `${tintColor}18`, borderColor: `${tintColor}40` }]}>
          <Text style={[styles.avatarText, { color: tintColor }]}>{getInitials(name, email)}</Text>
        </View>
        <Text numberOfLines={1} style={[styles.name, { color: textColor }]}>
          {name}
        </Text>
        <Text numberOfLines={1} style={[styles.email, { color: mutedColor }]}>
          {email}
        </Text>
      </View>

      <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
        {actions.map((action, index) => (
          <TouchableOpacity
            key={action.key}
            accessibilityRole="button"
            activeOpacity={0.8}
            onPress={action.onPress}
            style={[
              styles.actionRow,
              index < actions.length - 1 ? { borderBottomWidth: 1, borderBottomColor: borderColor } : null,
            ]}
          >
            <View style={styles.actionLeft}>
              <Ionicons
                name={action.icon}
                size={18}
                color={action.danger ? '#dc2626' : textColor}
              />
              <Text style={[styles.actionLabel, { color: action.danger ? '#dc2626' : textColor }]}>
                {action.label}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={16} color={mutedColor} />
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  drawer: {
    width: '78%',
    maxWidth: 320,
    height: '100%',
    borderRightWidth: 1,
    paddingTop: 54,
    paddingHorizontal: 16,
    gap: 18,
  },
  profileCard: {
    gap: 8,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 18,
    fontWeight: '800',
  },
  name: {
    fontSize: 18,
    fontWeight: '800',
  },
  email: {
    fontSize: 13,
    lineHeight: 18,
  },
  sectionCard: {
    borderWidth: 1,
    borderRadius: 16,
    overflow: 'hidden',
  },
  actionRow: {
    minHeight: 56,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  actionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  actionLabel: {
    fontSize: 15,
    fontWeight: '700',
  },
});
