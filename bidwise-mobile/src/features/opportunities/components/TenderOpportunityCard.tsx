import { useEffect, useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

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
import {
  formatDisplayValue,
  getExtraData,
  getProjectDocuments,
  hasDisplayValue,
} from '../utils/opportunityHelpers';
import {
  isOpportunitySaved,
  listenSavedOpportunityChanges,
  toggleSavedOpportunity,
} from '../utils/savedOpportunitiesStorage';
import OpportunityLogo from './OpportunityLogo';

interface TenderOpportunityCardProps {
  item: Opportunity;
  cardColor: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
  isUserAuthenticated: boolean;
  onPress: () => void;
  onRequireLogin: () => void;
}

type FactChipProps = {
  label: string;
  value: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
};

function FactChip({ label, value, borderColor, textColor, mutedColor }: FactChipProps) {
  if (!value) return null;

  return (
    <View style={[styles.factChip, { borderColor }]}>
      <Text style={[styles.factLabel, { color: mutedColor }]}>{label}</Text>
      <Text numberOfLines={1} style={[styles.factValue, { color: textColor }]}>
        {value}
      </Text>
    </View>
  );
}

export default function TenderOpportunityCard({
  item,
  cardColor,
  borderColor,
  textColor,
  mutedColor,
  tintColor,
  isUserAuthenticated,
  onPress,
  onRequireLogin,
}: TenderOpportunityCardProps) {
  const [isSaved, setIsSaved] = useState(false);
  const extraData = getExtraData(item);
  const structuredProjectData =
    extraData.structured && typeof extraData.structured === 'object'
      ? (extraData.structured as Record<string, unknown>)
      : {};
  const documents = getProjectDocuments(item);
  const lots = Array.isArray(extraData.lots) ? extraData.lots.filter(Boolean) : [];

  const organizationLabel = getOrganizationLabel(item);
  const typeLabel = formatTypeLabel(item.type_opportunite);
  const statusLabel = formatStatusLabel(item.statut);
  const sourceLabel = String(item.source?.nom || '').trim();
  const title = getOpportunityTitle(item);
  const descriptionPreview = getDescriptionPreview(item);
  const regionLabel = formatDisplayValue(extraData.region || extraData.region_execution || item.ville);
  const procedureLabel = formatDisplayValue(structuredProjectData.procedure || extraData.procedure);
  const fundingLabel = formatDisplayValue(structuredProjectData.financement || extraData.financement);
  const deadlineLabel = item.date_limite ? formatDate(item.date_limite) : '';
  const documentsLabel = documents.length ? `${documents.length} file${documents.length > 1 ? 's' : ''}` : '';
  const lotsLabel = lots.length ? `${lots.length} lot${lots.length > 1 ? 's' : ''}` : '';
  const publishedLabel = item.date_publication ? formatDate(item.date_publication) : '';

  useEffect(() => {
    let isMounted = true;

    if (!isUserAuthenticated || !item.id) {
      setIsSaved(false);
      return undefined;
    }

    const sync = async () => {
      const nextValue = await isOpportunitySaved(item.id);
      if (isMounted) {
        setIsSaved(nextValue);
      }
    };

    void sync();
    const unsubscribe = listenSavedOpportunityChanges(() => {
      void sync();
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [isUserAuthenticated, item.id]);

  const handleSavePress = async () => {
    if (!isUserAuthenticated) {
      onRequireLogin();
      return;
    }

    if (!item.id) return;
    const nextValue = await toggleSavedOpportunity(item.id);
    setIsSaved(nextValue);
  };

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Open tender ${title}`}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: cardColor,
          borderColor,
          opacity: pressed ? 0.96 : 1,
        },
      ]}
      onPress={onPress}
    >
      <View style={styles.headerRow}>
        <OpportunityLogo
          logoUrl={getCompanyLogoUrl(item)}
          sourceName={sourceLabel || 'MarchesPublics'}
          borderColor={borderColor}
          cardColor={cardColor}
          size={52}
        />

        <View style={styles.headerText}>
          <View style={styles.badgeRow}>
            <View style={[styles.primaryBadge, { backgroundColor: `${tintColor}14`, borderColor: `${tintColor}22` }]}>
              <Text style={[styles.primaryBadgeText, { color: tintColor }]}>{typeLabel}</Text>
            </View>
            <View style={[styles.secondaryBadge, { borderColor }]}>
              <Text style={[styles.secondaryBadgeText, { color: textColor }]}>{statusLabel}</Text>
            </View>
            {sourceLabel ? (
              <View style={[styles.secondaryBadge, { borderColor }]}>
                <Text numberOfLines={1} style={[styles.secondaryBadgeText, { color: mutedColor }]}>
                  {sourceLabel}
                </Text>
              </View>
            ) : null}
          </View>

          <Text numberOfLines={2} style={[styles.title, { color: textColor }]}>
            {title}
          </Text>

          {organizationLabel ? (
            <Text numberOfLines={1} style={[styles.subtitle, { color: mutedColor }]}>
              Acheteur: {organizationLabel}
            </Text>
          ) : null}
        </View>
      </View>

      <View style={styles.metaGrid}>
        {hasDisplayValue(regionLabel) ? (
          <View style={styles.metaItem}>
            <Ionicons name="location-outline" size={14} color={mutedColor} />
            <Text numberOfLines={1} style={[styles.metaText, { color: mutedColor }]}>
              {regionLabel}
            </Text>
          </View>
        ) : null}
        {deadlineLabel ? (
          <View style={styles.metaItem}>
            <Ionicons name="time-outline" size={14} color={mutedColor} />
            <Text numberOfLines={1} style={[styles.metaText, { color: mutedColor }]}>
              Deadline {deadlineLabel}
            </Text>
          </View>
        ) : null}
      </View>

      <View style={styles.factGrid}>
        <FactChip
          label="Procedure"
          value={procedureLabel}
          borderColor={borderColor}
          textColor={textColor}
          mutedColor={mutedColor}
        />
        <FactChip
          label="Funding"
          value={fundingLabel}
          borderColor={borderColor}
          textColor={textColor}
          mutedColor={mutedColor}
        />
        <FactChip
          label="Documents"
          value={documentsLabel}
          borderColor={borderColor}
          textColor={textColor}
          mutedColor={mutedColor}
        />
        <FactChip
          label="Lots"
          value={lotsLabel}
          borderColor={borderColor}
          textColor={textColor}
          mutedColor={mutedColor}
        />
      </View>

      <Text numberOfLines={3} style={[styles.description, { color: mutedColor }]}>
        {descriptionPreview}
      </Text>

      <View style={[styles.footerRow, { borderTopColor: borderColor }]}>
        <Text style={[styles.footerHint, { color: mutedColor }]}>
          {publishedLabel ? `Published ${publishedLabel}` : 'Public tender'}
        </Text>
        <View style={styles.footerActions}>
          <TouchableOpacity
            activeOpacity={0.85}
            onPress={() => {
              void handleSavePress();
            }}
            style={[styles.saveButton, { borderColor, backgroundColor: isSaved ? `${tintColor}12` : 'transparent' }]}
          >
            <Ionicons
              name={isSaved ? 'bookmark' : 'bookmark-outline'}
              size={15}
              color={isSaved ? tintColor : mutedColor}
            />
            <Text style={[styles.saveButtonText, { color: isSaved ? tintColor : textColor }]}>
              {isSaved ? 'Saved' : 'Save'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            activeOpacity={0.85}
            onPress={onPress}
            style={[styles.primaryCta, { backgroundColor: tintColor }]}
          >
            <Text style={styles.primaryCtaText}>View</Text>
          </TouchableOpacity>
        </View>
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
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  headerText: {
    flex: 1,
    gap: 6,
    minWidth: 0,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  primaryBadge: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  primaryBadgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  secondaryBadge: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    maxWidth: 140,
  },
  secondaryBadgeText: {
    fontSize: 11,
    fontWeight: '600',
  },
  title: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 13,
    fontWeight: '500',
  },
  metaGrid: {
    gap: 8,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  metaText: {
    flex: 1,
    fontSize: 13,
    lineHeight: 18,
  },
  factGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  factChip: {
    minWidth: '47%',
    flexGrow: 1,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  factLabel: {
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginBottom: 3,
  },
  factValue: {
    fontSize: 12,
    fontWeight: '700',
  },
  description: {
    fontSize: 13,
    lineHeight: 20,
  },
  footerRow: {
    borderTopWidth: 1,
    paddingTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  footerHint: {
    flex: 1,
    fontSize: 12,
    fontWeight: '500',
  },
  footerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  saveButton: {
    minHeight: 36,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  saveButtonText: {
    fontSize: 12,
    fontWeight: '700',
  },
  primaryCta: {
    minHeight: 36,
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
