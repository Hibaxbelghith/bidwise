import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export type AppTabKey = 'explore' | 'for-you' | 'dashboard' | 'profile';

type MobileTabBarProps = {
  currentTab: AppTabKey;
  onTabPress: (tab: AppTabKey) => void;
  isAuthenticated: boolean;
  backgroundColor: string;
  borderColor: string;
  cardColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
  hideForYou?: boolean;
};

const TAB_CONFIG: { key: AppTabKey; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: 'explore', label: 'Explore', icon: 'compass-outline' },
  { key: 'for-you', label: 'For You', icon: 'sparkles-outline' },
  { key: 'dashboard', label: 'Dashboard', icon: 'grid-outline' },
  { key: 'profile', label: 'Profile', icon: 'person-outline' },
];

export default function MobileTabBar({
  currentTab,
  onTabPress,
  isAuthenticated,
  backgroundColor,
  borderColor,
  cardColor,
  textColor,
  mutedColor,
  tintColor,
  hideForYou = false,
}: MobileTabBarProps) {
  const insets = useSafeAreaInsets();
  const visibleTabs = hideForYou ? TAB_CONFIG.filter((tab) => tab.key !== 'for-you') : TAB_CONFIG;

  return (
    <View
      style={[
        styles.wrapper,
        {
          backgroundColor,
          borderColor,
          paddingBottom: Math.max(insets.bottom, 14),
        },
      ]}
    >
      {visibleTabs.map((tab) => {
        const active = currentTab === tab.key;
        const locked = !isAuthenticated && tab !== 'explore';
        return (
          <TouchableOpacity
            key={tab.key}
            accessibilityRole="button"
            accessibilityLabel={`Open ${tab.label}`}
            activeOpacity={0.85}
            onPress={() => onTabPress(tab.key)}
            style={[
              styles.tabButton,
              {
                backgroundColor: active ? `${tintColor}14` : cardColor,
                borderColor: active ? `${tintColor}55` : 'transparent',
                opacity: locked ? 0.72 : 1,
              },
            ]}
          >
            <View style={styles.iconWrap}>
              <Ionicons
                name={active ? (tab.icon.replace('-outline', '') as keyof typeof Ionicons.glyphMap) : tab.icon}
                size={18}
                color={active ? tintColor : mutedColor}
              />
              {locked ? <Ionicons name="lock-closed" size={10} color={mutedColor} style={styles.lockIcon} /> : null}
            </View>
            <Text style={[styles.tabLabel, { color: active ? textColor : mutedColor }]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    borderTopWidth: 1,
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 14,
    flexDirection: 'row',
    gap: 8,
  },
  tabButton: {
    flex: 1,
    minHeight: 54,
    borderRadius: 14,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  iconWrap: {
    position: 'relative',
    width: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  lockIcon: {
    position: 'absolute',
    right: -6,
    top: -2,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: '700',
  },
});
