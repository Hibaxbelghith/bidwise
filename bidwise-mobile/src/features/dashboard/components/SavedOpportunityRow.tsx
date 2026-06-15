import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Opportunity } from '@/src/features/opportunities/services/opportunitiesService';
import {
  formatPublishedAgo,
  formatStatusLabel,
  formatTypeLabel,
  getOrganizationLabel,
  getOpportunityTitle,
} from '@/src/features/opportunities/utils/opportunityFormatters';

type SavedOpportunityRowProps = {
  item: Opportunity;
  textColor: string;
  mutedColor: string;
  borderColor: string;
  cardColor: string;
  tintColor: string;
  onPress: () => void;
};

export default function SavedOpportunityRow({
  item,
  textColor,
  mutedColor,
  borderColor,
  cardColor,
  tintColor,
  onPress,
}: SavedOpportunityRowProps) {
  const title = getOpportunityTitle(item);
  const organization = getOrganizationLabel(item);
  const location = String(item.ville || item.location || '').trim();
  const metaLabel = [formatTypeLabel(item.type_opportunite || item.type), location].filter(Boolean).join(' • ');
  const secondaryMeta = [organization, formatStatusLabel(item.statut), formatPublishedAgo(item.date_publication)]
    .filter(Boolean)
    .join(' • ');

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={[styles.card, { backgroundColor: cardColor, borderColor }]}
    >
      <View style={styles.content}>
        <Text numberOfLines={2} style={[styles.title, { color: textColor }]}>
          {title}
        </Text>
        {metaLabel ? (
          <Text numberOfLines={1} style={[styles.meta, { color: mutedColor }]}>
            {metaLabel}
          </Text>
        ) : null}
        {secondaryMeta ? (
          <Text numberOfLines={1} style={[styles.meta, { color: mutedColor }]}>
            {secondaryMeta}
          </Text>
        ) : null}
      </View>

      <View style={[styles.cta, { backgroundColor: `${tintColor}14` }]}>
        <Text style={[styles.ctaText, { color: tintColor }]}>View</Text>
        <Ionicons name="chevron-forward" size={16} color={tintColor} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  content: {
    flex: 1,
    gap: 6,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    lineHeight: 22,
  },
  meta: {
    fontSize: 13,
    lineHeight: 18,
  },
  cta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  ctaText: {
    fontSize: 13,
    fontWeight: '700',
  },
});
