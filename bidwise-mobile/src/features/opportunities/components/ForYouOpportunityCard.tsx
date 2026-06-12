import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import type { Opportunity } from '../services/opportunitiesService';
import {
  formatTypeLabel,
  getCompanyLogoUrl,
  getOpportunityTitle,
  getOrganizationLabel,
} from '../utils/opportunityFormatters';
import {
  getRecommendationConfidenceLabel,
  getRecommendationReasons,
  getRecommendationScorePercent,
  getRecommendationSignalChips,
  isStrongMatchRecommendation,
} from '../utils/recommendationUtils';
import OpportunityLogo from './OpportunityLogo';

type ForYouOpportunityCardProps = {
  item: Opportunity;
  onPress: () => void;
};

export default function ForYouOpportunityCard({
  item,
  onPress,
}: ForYouOpportunityCardProps) {
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const recommendation = item.recommendation || item;
  const organizationLabel = getOrganizationLabel(item);
  const title = getOpportunityTitle(item);
  const scorePercent = getRecommendationScorePercent(
    recommendation.score ?? recommendation.match_score,
  );
  const reasons = getRecommendationReasons(recommendation, 2);
  const signalChips = getRecommendationSignalChips(recommendation);
  const confidenceLabel = getRecommendationConfidenceLabel(recommendation);
  const isStrong = isStrongMatchRecommendation(recommendation);
  const location = String(item.ville || item.location || '').trim();

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Open recommended opportunity ${title}`}
      onPress={onPress}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: cardColor,
          borderColor: isStrong ? `${tintColor}66` : borderColor,
          opacity: pressed ? 0.94 : 1,
        },
      ]}
    >
      <View style={styles.headerRow}>
        <OpportunityLogo logoUrl={getCompanyLogoUrl(item)} />

        <View style={styles.headerTextWrap}>
          <Text numberOfLines={2} style={[styles.title, { color: textColor }]}>
            {title}
          </Text>
          {organizationLabel ? (
            <Text numberOfLines={1} style={[styles.organization, { color: mutedColor }]}>
              {organizationLabel}
            </Text>
          ) : null}
        </View>

        <View
          style={[
            styles.scoreBadge,
            {
              backgroundColor: isStrong ? `${tintColor}18` : `${tintColor}10`,
              borderColor: isStrong ? `${tintColor}60` : borderColor,
            },
          ]}
        >
          <Text style={[styles.scoreValue, { color: tintColor }]}>
            {scorePercent !== null ? `${scorePercent}%` : '--'}
          </Text>
          <Text style={[styles.scoreCaption, { color: mutedColor }]}>Match</Text>
        </View>
      </View>

      <View style={styles.metaRow}>
        <View style={[styles.metaChip, { borderColor }]}>
          <Text style={[styles.metaChipText, { color: textColor }]}>
            {formatTypeLabel(item.type_opportunite)}
          </Text>
        </View>
        {location ? (
          <Text numberOfLines={1} style={[styles.metaText, { color: mutedColor }]}>
            {location}
          </Text>
        ) : null}
      </View>

      {reasons.length ? (
        <View style={styles.reasonBlock}>
          {reasons.map((reason) => (
            <Text key={reason} numberOfLines={1} style={[styles.reasonText, { color: textColor }]}>
              {`\u2022 ${reason}`}
            </Text>
          ))}
        </View>
      ) : null}

      <View style={styles.footerRow}>
        <View style={styles.signalWrap}>
          {signalChips.map((chip) => (
            <View key={chip.key} style={[styles.signalChip, { borderColor }]}>
              <Text style={[styles.signalChipText, { color: mutedColor }]}>{chip.label}</Text>
            </View>
          ))}
        </View>
        <Text style={[styles.confidenceText, { color: mutedColor }]}>{confidenceLabel}</Text>
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
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  headerTextWrap: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    lineHeight: 22,
    fontWeight: '700',
    marginBottom: 4,
  },
  organization: {
    fontSize: 13,
  },
  scoreBadge: {
    minWidth: 58,
    borderWidth: 1,
    borderRadius: 12,
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 7,
  },
  scoreValue: {
    fontSize: 14,
    fontWeight: '700',
  },
  scoreCaption: {
    fontSize: 11,
    fontWeight: '700',
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 8,
    marginTop: 12,
  },
  metaChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  metaChipText: {
    fontSize: 12,
    fontWeight: '700',
  },
  metaText: {
    flexShrink: 1,
    fontSize: 12,
    fontWeight: '600',
  },
  reasonBlock: {
    marginTop: 12,
    gap: 4,
  },
  reasonText: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '600',
  },
  footerRow: {
    marginTop: 12,
    gap: 10,
  },
  signalWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  signalChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  signalChipText: {
    fontSize: 11,
    fontWeight: '700',
  },
  confidenceText: {
    fontSize: 12,
    fontWeight: '600',
  },
});
