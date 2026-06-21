import { useEffect, useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import type { Opportunity } from '../services/opportunitiesService';
import {
  formatContractTypeLabel,
  formatDate,
  formatExperienceLabel,
  formatPublishedAgo,
  formatStatusLabel,
  formatTypeLabel,
  formatWorkModeLabel,
  getCompanyLogoUrl,
  getDescriptionPreview,
  getOpportunityTitle,
  getOrganizationLabel,
  getSkillsPreview,
} from '../utils/opportunityFormatters';
import {
  isOpportunitySaved,
  listenSavedOpportunityChanges,
  toggleSavedOpportunity,
} from '../utils/savedOpportunitiesStorage';
import OpportunityLogo from './OpportunityLogo';
import TenderOpportunityCard from './TenderOpportunityCard';

interface OpportunityCardProps {
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

type MetaItemProps = {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  mutedColor: string;
};

function MetaItem({ icon, label, mutedColor }: MetaItemProps) {
  if (!label) return null;

  return (
    <View style={styles.metaItem}>
      <Ionicons name={icon} size={14} color={mutedColor} />
      <Text numberOfLines={1} style={[styles.metaText, { color: mutedColor }]}>
        {label}
      </Text>
    </View>
  );
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
  onRequireLogin,
}: OpportunityCardProps) {
  const [isSaved, setIsSaved] = useState(false);
  const isProject = String(item.type_opportunite || '').trim().toUpperCase() === 'PROJET';
  const organizationLabel = getOrganizationLabel(item);
  const typeLabel = formatTypeLabel(item.type_opportunite);
  const statusLabel = formatStatusLabel(item.statut);
  const sourceLabel = String(item.source?.nom || '').trim();
  const salaryLabel = String(item.salary || '').trim();
  const contractLabel = formatContractTypeLabel(item.contract_type);
  const workModeLabel = formatWorkModeLabel(item.normalized_work_mode || item.availability);
  const experienceLabel = formatExperienceLabel(item);
  const descriptionPreview = getDescriptionPreview(item);
  const skillsPreview = getSkillsPreview(item, 4);
  const allSkillValues = [
    ...(Array.isArray(item.normalized_skills) ? item.normalized_skills : []),
    ...(Array.isArray(item.skills) ? item.skills : []),
  ]
    .map((value) => String(value || '').trim())
    .filter(Boolean);
  const totalSkills = new Set(allSkillValues.map((value) => value.toLowerCase())).size;
  const locationLabel = String(item.ville || '').trim();
  const deadlineLabel = item.date_limite ? `Deadline ${formatDate(item.date_limite)}` : '';
  const publishedAgoLabel = formatPublishedAgo(item.date_publication);

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

  if (isProject) {
    return (
      <TenderOpportunityCard
        item={item}
        cardColor={cardColor}
        borderColor={borderColor}
        textColor={textColor}
        mutedColor={mutedColor}
        tintColor={tintColor}
        isUserAuthenticated={isUserAuthenticated}
        onPress={onPress}
        onRequireLogin={onRequireLogin}
      />
    );
  }

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Open opportunity ${getOpportunityTitle(item)}`}
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
          sourceName={sourceLabel}
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
            {getOpportunityTitle(item)}
          </Text>

          {organizationLabel ? (
            <Text numberOfLines={1} style={[styles.subtitle, { color: mutedColor }]}>
              {organizationLabel}
            </Text>
          ) : null}
        </View>
      </View>

      <View style={styles.metaGrid}>
        <MetaItem icon="location-outline" label={locationLabel} mutedColor={mutedColor} />
        <MetaItem icon="time-outline" label={deadlineLabel || formatDate(item.date_publication)} mutedColor={mutedColor} />
        <MetaItem icon="briefcase-outline" label={workModeLabel} mutedColor={mutedColor} />
      </View>

      {(salaryLabel || contractLabel || experienceLabel) ? (
        <View style={styles.chipRow}>
          {salaryLabel ? (
            <View style={[styles.infoChip, { borderColor }]}>
              <Text style={[styles.infoChipText, { color: textColor }]}>{salaryLabel}</Text>
            </View>
          ) : null}
          {contractLabel ? (
            <View style={[styles.infoChip, { borderColor }]}>
              <Text style={[styles.infoChipText, { color: textColor }]}>{contractLabel}</Text>
            </View>
          ) : null}
          {experienceLabel ? (
            <View style={[styles.infoChip, { borderColor }]}>
              <Text style={[styles.infoChipText, { color: textColor }]}>{experienceLabel}</Text>
            </View>
          ) : null}
        </View>
      ) : null}

      <Text numberOfLines={3} style={[styles.description, { color: mutedColor }]}>
        {descriptionPreview}
      </Text>

      {skillsPreview.length > 0 ? (
        <View style={styles.skillsRow}>
          {skillsPreview.map((skill) => (
            <View key={skill} style={[styles.skillChip, { borderColor }]}>
              <Text numberOfLines={1} style={[styles.skillChipText, { color: textColor }]}>
                {skill}
              </Text>
            </View>
          ))}
          {totalSkills > skillsPreview.length ? (
            <View style={[styles.skillChip, { borderColor }]}>
              <Text style={[styles.skillChipText, { color: mutedColor }]}>
                +{totalSkills - skillsPreview.length}
              </Text>
            </View>
          ) : null}
        </View>
      ) : null}

      <View style={[styles.footerRow, { borderTopColor: borderColor }]}>
        <Text style={[styles.footerHint, { color: mutedColor }]}>
          {publishedAgoLabel ? `Published ${publishedAgoLabel}` : `Published ${formatDate(item.date_publication)}`}
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
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  infoChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  infoChipText: {
    fontSize: 12,
    fontWeight: '600',
  },
  description: {
    fontSize: 13,
    lineHeight: 20,
  },
  skillsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
    maxWidth: 140,
  },
  skillChipText: {
    fontSize: 12,
    fontWeight: '600',
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
