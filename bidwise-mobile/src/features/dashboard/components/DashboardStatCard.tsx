import { StyleSheet, Text, View } from 'react-native';

type DashboardStatCardProps = {
  value: string | number;
  label: string;
  cardColor: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
};

export default function DashboardStatCard({
  value,
  label,
  cardColor,
  borderColor,
  textColor,
  mutedColor,
}: DashboardStatCardProps) {
  return (
    <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
      <Text style={[styles.value, { color: textColor }]}>{value}</Text>
      <Text style={[styles.label, { color: mutedColor }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minHeight: 92,
    borderWidth: 1,
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 16,
    justifyContent: 'center',
    gap: 6,
  },
  value: {
    fontSize: 24,
    fontWeight: '700',
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
  },
});
