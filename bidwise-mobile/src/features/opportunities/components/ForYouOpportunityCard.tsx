import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import type { Opportunity } from '../services/opportunitiesService';
import {
  formatDate,
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
  const publishedAt = item.date_publication ? formatDate(item.date_publication) : '';
  const typeLabel = formatTypeLabel(item.type_opportunite);
  const sourceLabel = String(item.source?.nom || '').trim();
  const isTender = String(item.type_opportunite || item.type || '').trim().toUpperCase() === 'PROJET';
  const primaryBadgeLabel = isTender
    ? isStrong
      ? 'Strong priority'
      : 'Watch closely'
    : isStrong
      ? 'Strong match'
      : 'Review';

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Open recommended opportunity ${title}`}
      onPress={onPress}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: cardColor,
          borderColor: isStrong ? `${tintColor}55` : borderColor,
          opacity: pressed ? 0.96 : 1,
        },
      ]}
    >
      <View style={styles.topRow}>
        <View
          style={[
            styles.recommendationBadge,
            {
              backgroundColor: isStrong ? `${tintColor}16` : `${tintColor}10`,
              borderColor: isStrong ? `${tintColor}35` : borderColor,
            },
          ]}
        >
          <Ionicons
            name={isStrong ? 'sparkles' : 'eye-outline'}
            size={12}
            color={isStrong ? tintColor : mutedColor}
          />
          <Text style={[styles.recommendationBadgeText, { color: isStrong ? tintColor : mutedColor }]}>
            {primaryBadgeLabel}
          </Text>
        </View>

        <View
          style={[
            styles.scoreBadge,
            {
              backgroundColor: isStrong ? `${tintColor}18` : `${tintColor}10`,
              borderColor: isStrong ? `${tintColor}40` : borderColor,
            },
          ]}
        >
          <Text style={[styles.scoreValue, { color: tintColor }]}>
            {scorePercent !== null ? `${scorePercent}%` : '--'}
          </Text>
          <Text style={[styles.scoreCaption, { color: mutedColor }]}>
            {isTender ? 'Priority' : 'Match'}
          </Text>
        </View>
      </View>

      <View style={styles.headerRow}>
        <OpportunityLogo
          logoUrl={getCompanyLogoUrl(item)}
          sourceName={sourceLabel || (isTender ? 'MarchesPublics' : '')}
          size={50}
        />

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
      </View>

      <View style={styles.metaRow}>
        <View style={[styles.metaChip, { borderColor }]}>
          <Text style={[styles.metaChipText, { color: textColor }]}>{typeLabel}</Text>
        </View>
        {location ? (
          <View style={styles.metaInline}>
            <Ionicons name="location-outline" size={13} color={mutedColor} />
            <Text numberOfLines={1} style={[styles.metaText, { color: mutedColor }]}>
              {location}
            </Text>
          </View>
        ) : null}
        {publishedAt ? (
          <View style={styles.metaInline}>
            <Ionicons name="time-outline" size={13} color={mutedColor} />
            <Text numberOfLines={1} style={[styles.metaText, { color: mutedColor }]}>
              {publishedAt}
            </Text>
          </View>
        ) : null}
      </View>

      {reasons.length ? (
        <View style={styles.reasonBlock}>
          {reasons.map((reason) => (
            <View key={reason} style={styles.reasonRow}>
              <Ionicons name="checkmark-circle-outline" size={14} color={tintColor} />
              <Text numberOfLines={2} style={[styles.reasonText, { color: textColor }]}>
                {reason}
              </Text>
            </View>
          ))}
        </View>
      ) : null}

      <View style={styles.footerRow}>
        <View style={styles.footerLeft}>
          <View style={styles.signalWrap}>
            {signalChips.map((chip) => (
              <View key={chip.key} style={[styles.signalChip, { borderColor }]}>
                <Text style={[styles.signalChipText, { color: mutedColor }]}>{chip.label}</Text>
              </View>
            ))}
          </View>
          <Text style={[styles.confidenceText, { color: mutedColor }]}>{confidenceLabel}</Text>
        </View>

        <TouchableOpacity
          activeOpacity={0.85}
          onPress={onPress}
          style={[styles.primaryCta, { backgroundColor: tintColor }]}
        >
          <Text style={styles.primaryCtaText}>View</Text>
        </TouchableOpacity>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    gap: 14,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  recommendationBadge: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  recommendationBadgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  scoreBadge: {
    minWidth: 60,
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
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  headerTextWrap: {
    flex: 1,
    minWidth: 0,
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
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 10,
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
  metaInline: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    maxWidth: 120,
  },
  metaText: {
    flexShrink: 1,
    fontSize: 12,
    fontWeight: '600',
  },
  reasonBlock: {
    gap: 8,
  },
  reasonRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  reasonText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 19,
    fontWeight: '600',
  },
  footerRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    gap: 12,
  },
  footerLeft: {
    flex: 1,
    gap: 8,
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
  primaryCta: {
    minHeight: 38,
    borderRadius: 10,
    paddingHorizontal: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryCtaText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '700',
  },
});
