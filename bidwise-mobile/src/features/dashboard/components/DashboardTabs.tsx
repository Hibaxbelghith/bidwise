import { Pressable, StyleSheet, Text, View } from 'react-native';

type DashboardTabKey = 'saved' | 'applications';

type DashboardTabsProps = {
  value: DashboardTabKey;
  onChange: (value: DashboardTabKey) => void;
  savedCount: number;
  applicationsCount: number;
  cardColor: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
};

const TABS: { key: DashboardTabKey; label: string }[] = [
  { key: 'saved', label: 'Saved' },
  { key: 'applications', label: 'Applications' },
];

export default function DashboardTabs({
  value,
  onChange,
  savedCount,
  applicationsCount,
  cardColor,
  borderColor,
  textColor,
  mutedColor,
  tintColor,
}: DashboardTabsProps) {
  return (
    <View style={[styles.wrap, { backgroundColor: cardColor, borderColor }]}>
      {TABS.map((tab) => {
        const active = tab.key === value;
        const count = tab.key === 'saved' ? savedCount : applicationsCount;

        return (
          <Pressable
            key={tab.key}
            accessibilityRole="button"
            onPress={() => onChange(tab.key)}
            style={[
              styles.tab,
              active ? { backgroundColor: `${tintColor}14`, borderColor: `${tintColor}45` } : null,
            ]}
          >
            <Text style={[styles.tabLabel, { color: active ? textColor : mutedColor }]}>
              {tab.label}
            </Text>
            <View
              style={[
                styles.countBadge,
                {
                  backgroundColor: active ? `${tintColor}18` : 'rgba(148, 163, 184, 0.16)',
                },
              ]}
            >
              <Text style={[styles.countText, { color: active ? tintColor : mutedColor }]}>{count}</Text>
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 6,
    flexDirection: 'row',
    gap: 8,
  },
  tab: {
    flex: 1,
    minHeight: 44,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'transparent',
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  tabLabel: {
    fontSize: 14,
    fontWeight: '700',
  },
  countBadge: {
    minWidth: 24,
    height: 24,
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 7,
  },
  countText: {
    fontSize: 12,
    fontWeight: '700',
  },
});
