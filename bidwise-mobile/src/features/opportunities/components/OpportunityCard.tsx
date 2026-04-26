import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Opportunity } from '../services/opportunitiesService';
import {
  formatDate,
  formatStatusLabel,
  formatTypeLabel,
  getCompanyLogoUrl,
  getDescriptionPreview,
  getOpportunityTitle,
  getOrganizationLabel,
} from '../utils/opportunityFormatters';
import OpportunityLogo from './OpportunityLogo';

interface OpportunityCardProps {
  item: Opportunity;
  cardColor: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
  isUserAuthenticated: boolean;
  onPress: () => void;
}

export default function OpportunityCard({
  item,
  cardColor,
  borderColor,
  textColor,
  mutedColor,
  tintColor,
  isUserAuthenticated,
  onPress,
}: OpportunityCardProps) {
  const salaryLabel = String(item.salary || '').trim();
  const organizationLabel = getOrganizationLabel(item);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Open opportunity ${getOpportunityTitle(item)}`}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: cardColor,
          borderColor,
          opacity: pressed ? 0.92 : 1,
        },
      ]}
      onPress={onPress}
    >
      <View style={styles.cardHeader}>
        <OpportunityLogo
          logoUrl={getCompanyLogoUrl(item)}
          borderColor={borderColor}
          cardColor={cardColor}
        />

        <View style={styles.cardHeaderTextWrap}>
          <Text numberOfLines={2} style={[styles.cardTitle, { color: textColor }]}>
            {getOpportunityTitle(item)}
          </Text>
          {organizationLabel ? (
            <Text numberOfLines={1} style={[styles.cardSubtitle, { color: mutedColor }]}>
              {organizationLabel}
            </Text>
          ) : null}
        </View>
      </View>

      <View style={styles.chipsRow}>
        <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}18` }]}>
          <Text style={[styles.chipText, { color: tintColor }]}>{formatTypeLabel(item.type_opportunite)}</Text>
        </View>
        {salaryLabel ? (
          <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}10` }]}>
            <Text style={[styles.chipText, { color: textColor }]}>{salaryLabel}</Text>
          </View>
        ) : null}
        <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}10` }]}>
          <Text style={[styles.chipText, { color: textColor }]}>{formatStatusLabel(item.statut)}</Text>
        </View>
      </View>

      <Text style={[styles.metaText, { color: mutedColor }]}>📍 {String(item.ville || '').trim() || 'N/A'}</Text>
      <Text style={[styles.metaText, { color: mutedColor }]}>📅 {formatDate(item.date_publication)}</Text>

      <Text numberOfLines={2} style={[styles.descriptionText, { color: mutedColor }]}>
        {getDescriptionPreview(item)}
      </Text>

      <View style={styles.cardFooterRow}>
        <Text style={[styles.cardFooterHint, { color: mutedColor }]}>
          {isUserAuthenticated ? 'AI insights in detail' : 'AI features locked'}
        </Text>
        <Text style={[styles.cardFooterCta, { color: tintColor }]}>View</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  cardHeaderTextWrap: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 3,
  },
  cardSubtitle: {
    fontSize: 13,
  },
  chipsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 10,
  },
  chip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  chipText: {
    fontSize: 12,
    fontWeight: '700',
  },
  metaText: {
    fontSize: 12,
    marginBottom: 5,
  },
  descriptionText: {
    fontSize: 13,
    lineHeight: 18,
    marginTop: 6,
  },
  cardFooterRow: {
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#a1a1aa55',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardFooterHint: {
    fontSize: 12,
    fontWeight: '600',
  },
  cardFooterCta: {
    fontSize: 13,
    fontWeight: '800',
  },
});
