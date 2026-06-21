import { useCallback } from 'react';
import {
  Alert,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import { useOpportunityDetail } from '../hooks/useOpportunityDetail';
import {
  formatDate,
  formatExperienceLabel,
  formatProjectDocumentType,
  formatStatusLabel,
  formatTypeLabel,
} from '../utils/opportunityFormatters';
import { formatDisplayValue, hasDisplayValue } from '../utils/opportunityHelpers';
import { toggleSavedOpportunity } from '../utils/savedOpportunitiesStorage';
import OpportunityLogo from './OpportunityLogo';

const DESCRIPTION_LINES_COLLAPSED = 7;

interface FactRowProps {
  borderColor: string;
  icon: string;
  label: string;
  mutedColor: string;
  textColor: string;
  value: string;
}

function FactRow({
  borderColor,
  icon,
  label,
  mutedColor,
  textColor,
  value,
}: FactRowProps) {
  if (!value) return null;

  return (
    <View style={[styles.factRow, { borderColor }]}>
      <Text style={[styles.factLabel, { color: mutedColor }]}>
        {icon && icon !== label ? `${icon} ` : ''}
        {label}
      </Text>
      <Text style={[styles.factValue, { color: textColor }]}>{value}</Text>
    </View>
  );
}

function DetailSkeleton({
  borderColor,
  cardColor,
  skeletonBase,
  skeletonSoft,
}: {
  borderColor: string;
  cardColor: string;
  skeletonBase: string;
  skeletonSoft: string;
}) {
  return (
    <View style={styles.skeletonContainer}>
      <View style={[styles.mainCard, { backgroundColor: cardColor, borderColor }]}>
        <View
          style={[
            styles.skeletonBlock,
            { width: '78%', height: 18, marginBottom: 10, backgroundColor: skeletonBase },
          ]}
        />
        <View
          style={[
            styles.skeletonBlock,
            { width: '52%', height: 12, backgroundColor: skeletonSoft },
          ]}
        />
      </View>

      <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
        <View
          style={[
            styles.skeletonBlock,
            { width: '100%', height: 12, marginBottom: 8, backgroundColor: skeletonSoft },
          ]}
        />
        <View
          style={[
            styles.skeletonBlock,
            { width: '88%', height: 12, marginBottom: 8, backgroundColor: skeletonSoft },
          ]}
        />
        <View
          style={[
            styles.skeletonBlock,
            { width: '74%', height: 12, backgroundColor: skeletonSoft },
          ]}
        />
      </View>

      <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
        {[0, 1, 2].map((index) => (
          <View
            key={index}
            style={[
              styles.skeletonBlock,
              { width: '100%', height: 48, marginBottom: 8, backgroundColor: skeletonSoft },
            ]}
          />
        ))}
      </View>
    </View>
  );
}

export default function OpportunityDetailScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id?: string | string[] }>();
  const { isAuthenticated, loading: authLoading } = useAuth();

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const skeletonBase = useThemeColor({ light: '#d4d4d8', dark: '#2f2f2f' }, 'border');
  const skeletonSoft = useThemeColor({ light: '#e4e4e7', dark: '#3a3a3a' }, 'card');

  const isUserAuthenticated = !authLoading && isAuthenticated;
  const {
    additionalInfoItems,
    availabilityLabel,
    companyLabel,
    contractLabel,
    dedupedSimilar,
    description,
    educationLabel,
    error,
    fetchDetail,
    hasExtraData,
    hiddenSkillsCount,
    isDescriptionExpanded,
    isLongDescription,
    isProject,
    isSaved,
    item,
    languagesLabel,
    locationLabel,
    matchBullets,
    loading,
    projectDocuments,
    projectLots,
    projectProcedureLabel,
    projectRegionLabel,
    projectTypeCommandeLabel,
    projectFinancementLabel,
    projectDelaiValiditeLabel,
    projectCautionLabel,
    quickScanSkills,
    salaryLabel,
    semanticScore,
    setIsDescriptionExpanded,
    setIsSaved,
    setShowAllSkills,
    showAllSkills,
    similarError,
    similarLoading,
    skills,
    sourceLabel,
    tenderFactRows,
  } = useOpportunityDetail({
    idParam: id,
    isUserAuthenticated,
    onInvalidId: () => router.replace('/explore'),
  });

  const showSkeleton = loading || authLoading;
  const applyDisabled = isUserAuthenticated && !String(item?.source_item_url || '').trim();
  const visibleSkills = showAllSkills ? skills : quickScanSkills;

  const handleOpenLogin = useCallback(() => {
    router.push('/login');
  }, [router]);

  const handleOpenSimilarOpportunity = useCallback(
    (opportunityId: number) => {
      router.push({
        pathname: '/opportunities/[id]',
        params: { id: String(opportunityId) },
      });
    },
    [router],
  );

  const handleOpenDocument = useCallback(async (url: string) => {
    try {
      await Linking.openURL(url);
    } catch {
      Alert.alert('Document unavailable', 'Failed to open this document.');
    }
  }, []);

  const handleApplyPress = useCallback(async () => {
    if (!isUserAuthenticated) {
      handleOpenLogin();
      return;
    }

    const sourceUrl = String(item?.source_item_url || '').trim();
    if (!sourceUrl) {
      Alert.alert('Source unavailable', 'No source URL is available for this opportunity.');
      return;
    }

    try {
      const supported = await Linking.canOpenURL(sourceUrl);
      if (!supported) {
        Alert.alert('Source unavailable', 'This source URL cannot be opened on your device.');
        return;
      }

      await Linking.openURL(sourceUrl);
    } catch {
      Alert.alert('Source unavailable', 'Failed to open this source link.');
    }
  }, [handleOpenLogin, isUserAuthenticated, item?.source_item_url]);

  const handleSavePress = useCallback(async () => {
    if (!isUserAuthenticated) {
      handleOpenLogin();
      return;
    }

    if (!item?.id) return;
    const nextValue = await toggleSavedOpportunity(item.id);
    setIsSaved(nextValue);
  }, [handleOpenLogin, isUserAuthenticated, item?.id, setIsSaved]);

  return (
    <View style={[styles.root, { backgroundColor }]}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[
          styles.screen,
          {
            backgroundColor,
            paddingBottom: 132 + Math.max(insets.bottom, 10),
          },
        ]}
      >
        <View style={styles.topBar}>
          <Pressable
            accessibilityLabel="Back to opportunities"
            accessibilityRole="button"
            onPress={() => router.back()}
          >
            <Text style={[styles.backText, { color: tintColor }]}>Opportunities</Text>
          </Pressable>

          {!isUserAuthenticated ? (
            <Pressable
              accessibilityLabel="Quick login"
              accessibilityRole="button"
              onPress={handleOpenLogin}
              style={[styles.inlineLoginButton, { borderColor, backgroundColor: `${tintColor}18` }]}
            >
              <Text style={[styles.inlineLoginButtonText, { color: tintColor }]}>Quick login</Text>
            </Pressable>
          ) : null}
        </View>

        {showSkeleton ? (
          <DetailSkeleton
            borderColor={borderColor}
            cardColor={cardColor}
            skeletonBase={skeletonBase}
            skeletonSoft={skeletonSoft}
          />
        ) : null}

        {!showSkeleton && error ? (
          <View style={[styles.errorCard, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.errorTitle, { color: textColor }]}>Unable to load opportunity</Text>
            <Text style={[styles.errorMessage, { color: mutedColor }]}>{error}</Text>
            <Pressable
              style={[styles.retryButton, { backgroundColor: tintColor }]}
              onPress={() => void fetchDetail()}
            >
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        ) : null}

        {!showSkeleton && !error && item ? (
          <>
            <View style={[styles.mainCard, { backgroundColor: cardColor, borderColor }]}>
              <View style={styles.headerRow}>
                <OpportunityLogo
                  logoUrl={String(item.company_logo || '').trim()}
                  borderColor={borderColor}
                  cardColor={cardColor}
                  size={52}
                />

                <View style={styles.headerContent}>
                  <Text style={[styles.title, { color: textColor }]}>
                    {String(item.titre || 'Untitled opportunity')}
                  </Text>
                  {companyLabel ? (
                    <Text style={[styles.companyText, { color: mutedColor }]}>{companyLabel}</Text>
                  ) : null}
                </View>
              </View>

              <View style={styles.chipRow}>
                <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}18` }]}>
                  <Text style={[styles.chipText, { color: tintColor }]}>
                    {formatTypeLabel(item.type_opportunite)}
                  </Text>
                </View>
                <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}10` }]}>
                  <Text style={[styles.chipText, { color: textColor }]}>
                    {formatStatusLabel(item.statut)}
                  </Text>
                </View>
                {!isProject ? (
                  <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}14` }]}>
                    <Text style={[styles.chipText, { color: tintColor }]}>
                      {isUserAuthenticated
                        ? semanticScore !== null
                          ? `Match ${semanticScore}%`
                          : 'Match --'
                        : 'Match locked'}
                    </Text>
                  </View>
                ) : null}
              </View>

              <Text style={[styles.metaText, { color: mutedColor }]}>Location: {locationLabel}</Text>
              <Text style={[styles.metaText, { color: mutedColor }]}>
                Published: {formatDate(item.date_publication)}
              </Text>
            </View>

            {!isProject && !isUserAuthenticated ? (
              <View style={[styles.guestLockStrip, { backgroundColor: cardColor, borderColor }]}>
                <View style={styles.guestLockStripTextWrap}>
                  <Text style={[styles.guestLockStripTitle, { color: textColor }]}>
                    AI features locked
                  </Text>
                  <Text style={[styles.guestLockStripText, { color: mutedColor }]}>
                    Login to unlock score, recommendations and actions.
                  </Text>
                </View>
                <Pressable
                  accessibilityLabel="Quick login"
                  accessibilityRole="button"
                  style={[styles.guestLockStripButton, { backgroundColor: tintColor }]}
                  onPress={handleOpenLogin}
                >
                  <Text style={styles.guestLockStripButtonText}>Quick login</Text>
                </Pressable>
              </View>
            ) : null}

            {!isProject ? (
              <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
                <Text style={[styles.sectionTitle, { color: textColor }]}>Quick scan</Text>

                <View style={styles.scanGrid}>
                  <FactRow
                    borderColor={borderColor}
                    icon="Salary"
                    label="Salary"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={salaryLabel}
                  />
                  <FactRow
                    borderColor={borderColor}
                    icon="Location"
                    label="Location"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={locationLabel}
                  />
                  <FactRow
                    borderColor={borderColor}
                    icon="Contract"
                    label="Contract"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={contractLabel}
                  />
                  <FactRow
                    borderColor={borderColor}
                    icon="Experience"
                    label="Experience"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={formatExperienceLabel(item)}
                  />
                  <FactRow
                    borderColor={borderColor}
                    icon="Company"
                    label="Company"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={companyLabel}
                  />
                  <FactRow
                    borderColor={borderColor}
                    icon="Source"
                    label="Source"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={sourceLabel || 'BidWise'}
                  />
                </View>

                <View style={[styles.scanGrid, styles.inlineSection]}>
                  <FactRow
                    borderColor={borderColor}
                    icon="Availability"
                    label="Availability"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={availabilityLabel}
                  />
                  <FactRow
                    borderColor={borderColor}
                    icon="Education"
                    label="Education"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={educationLabel}
                  />
                  <FactRow
                    borderColor={borderColor}
                    icon="Languages"
                    label="Languages"
                    mutedColor={mutedColor}
                    textColor={textColor}
                    value={languagesLabel}
                  />
                </View>

                <View style={styles.inlineSection}>
                  <View style={styles.inlineSectionHeader}>
                    <Text style={[styles.inlineSectionTitle, { color: mutedColor }]}>Skills</Text>
                    {skills.length > quickScanSkills.length ? (
                      <Pressable
                        accessibilityRole="button"
                        onPress={() => setShowAllSkills((previous) => !previous)}
                      >
                        <Text style={[styles.inlineActionText, { color: tintColor }]}>
                          {showAllSkills ? 'Show less' : `+${hiddenSkillsCount}`}
                        </Text>
                      </Pressable>
                    ) : null}
                  </View>

                  {visibleSkills.length ? (
                    <View style={styles.skillsWrap}>
                      {visibleSkills.map((skill) => (
                        <View key={skill} style={[styles.skillChip, { borderColor }]}>
                          <Text style={[styles.skillChipText, { color: textColor }]}>{skill}</Text>
                        </View>
                      ))}
                    </View>
                  ) : (
                    <Text style={[styles.sectionBody, { color: mutedColor }]}>
                      No structured skills.
                    </Text>
                  )}
                </View>
              </View>
            ) : null}

            {description ? (
              <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
                <View style={styles.inlineSectionHeader}>
                  <Text style={[styles.sectionTitle, { color: textColor }]}>Description</Text>
                  {isLongDescription ? (
                    <Pressable
                      accessibilityRole="button"
                      onPress={() => setIsDescriptionExpanded((previous) => !previous)}
                    >
                      <Text style={[styles.inlineActionText, { color: tintColor }]}>
                        {isDescriptionExpanded ? 'Less' : 'More'}
                      </Text>
                    </Pressable>
                  ) : null}
                </View>

                <Text
                  style={[styles.descriptionText, { color: mutedColor }]}
                  numberOfLines={isDescriptionExpanded ? undefined : DESCRIPTION_LINES_COLLAPSED}
                >
                  {description}
                </Text>
              </View>
            ) : null}

            {hasExtraData && additionalInfoItems.length ? (
              <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
                <Text style={[styles.sectionTitle, { color: textColor }]}>Additional information</Text>

                <View style={styles.scanGrid}>
                  {additionalInfoItems.map((detail) => (
                    <FactRow
                      key={detail.label}
                      borderColor={borderColor}
                      icon="Info"
                      label={detail.label}
                      mutedColor={mutedColor}
                      textColor={textColor}
                      value={detail.value}
                    />
                  ))}
                </View>
              </View>
            ) : null}

            {!isProject && projectDocuments.length ? (
              <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
                <Text style={[styles.sectionTitle, { color: textColor }]}>Documents</Text>

                <View style={styles.similarListWrap}>
                  {projectDocuments.map((document, index) => (
                    <Pressable
                      key={`${document.url}-${index}`}
                      accessibilityRole="button"
                      onPress={() => void handleOpenDocument(document.url)}
                      style={[styles.similarItemRow, { borderColor }]}
                    >
                      <Text style={[styles.similarItemTitle, { color: textColor }]} numberOfLines={2}>
                        {document.label || formatProjectDocumentType(document.type, document.label)}
                      </Text>
                      <Text style={[styles.similarItemCompany, { color: mutedColor }]}>
                        {formatProjectDocumentType(document.type, document.label)}
                      </Text>
                      <Text style={[styles.similarItemScore, { color: tintColor }]}>Open</Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            ) : null}

            {isProject ? (
              <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
                <Text style={[styles.sectionTitle, { color: textColor }]}>Tender details</Text>

                <View style={styles.scanGrid}>
                  {tenderFactRows.map((fact) => (
                    <FactRow
                      key={fact.label}
                      borderColor={borderColor}
                      icon={fact.icon}
                      label={fact.label}
                      mutedColor={mutedColor}
                      textColor={textColor}
                      value={fact.value}
                    />
                  ))}
                </View>

                {!tenderFactRows.length ? (
                  <View style={[styles.scanGrid, styles.inlineSection]}>
                    <FactRow
                      borderColor={borderColor}
                      icon="Region"
                      label="Region"
                      mutedColor={mutedColor}
                      textColor={textColor}
                      value={projectRegionLabel}
                    />
                    <FactRow
                      borderColor={borderColor}
                      icon="Procedure"
                      label="Procedure"
                      mutedColor={mutedColor}
                      textColor={textColor}
                      value={projectProcedureLabel}
                    />
                    <FactRow
                      borderColor={borderColor}
                      icon="Funding"
                      label="Funding"
                      mutedColor={mutedColor}
                      textColor={textColor}
                      value={projectFinancementLabel}
                    />
                    <FactRow
                      borderColor={borderColor}
                      icon="Command"
                      label="Command"
                      mutedColor={mutedColor}
                      textColor={textColor}
                      value={projectTypeCommandeLabel}
                    />
                    <FactRow
                      borderColor={borderColor}
                      icon="Validity"
                      label="Validity"
                      mutedColor={mutedColor}
                      textColor={textColor}
                      value={projectDelaiValiditeLabel}
                    />
                    <FactRow
                      borderColor={borderColor}
                      icon="Caution"
                      label="Caution"
                      mutedColor={mutedColor}
                      textColor={textColor}
                      value={projectCautionLabel}
                    />
                  </View>
                ) : null}

                {projectDocuments.length ? (
                  <View style={styles.inlineSection}>
                    <Text style={[styles.inlineSectionTitle, { color: mutedColor }]}>Documents</Text>
                    <View style={styles.similarListWrap}>
                      {projectDocuments.map((document, index) => (
                        <Pressable
                          key={`${document.url}-${index}`}
                          accessibilityRole="button"
                          onPress={() => void handleOpenDocument(document.url)}
                          style={[styles.similarItemRow, { borderColor }]}
                        >
                          <Text
                            style={[styles.similarItemTitle, { color: textColor }]}
                            numberOfLines={2}
                          >
                            {document.label || formatProjectDocumentType(document.type, document.label)}
                          </Text>
                          <Text style={[styles.similarItemCompany, { color: mutedColor }]}>
                            {formatProjectDocumentType(document.type, document.label)}
                          </Text>
                          <Text style={[styles.similarItemScore, { color: tintColor }]}>Open</Text>
                        </Pressable>
                      ))}
                    </View>
                  </View>
                ) : null}

                {projectLots.length ? (
                  <View style={styles.inlineSection}>
                    <Text style={[styles.inlineSectionTitle, { color: mutedColor }]}>Lots</Text>
                    <View style={styles.similarListWrap}>
                      {projectLots.map((lot, index) => {
                        const lotTitle = formatDisplayValue(lot?.lot) || `Lot ${index + 1}`;
                        const lotDetails = [
                          hasDisplayValue(lot?.objet) ? `Objet: ${formatDisplayValue(lot?.objet)}` : '',
                          hasDisplayValue(lot?.quantite)
                            ? `Quantite: ${formatDisplayValue(lot?.quantite)}`
                            : '',
                          hasDisplayValue(lot?.region) ? `Region: ${formatDisplayValue(lot?.region)}` : '',
                          hasDisplayValue(lot?.caution)
                            ? `Caution: ${formatDisplayValue(lot?.caution)}`
                            : '',
                        ].filter(Boolean);

                        return (
                          <View key={`${lotTitle}-${index}`} style={[styles.similarItemRow, { borderColor }]}>
                            <Text style={[styles.similarItemTitle, { color: textColor }]}>{lotTitle}</Text>
                            {lotDetails.map((detail) => (
                              <Text key={detail} style={[styles.sectionBody, { color: mutedColor }]}>
                                {detail}
                              </Text>
                            ))}
                          </View>
                        );
                      })}
                    </View>
                  </View>
                ) : null}
              </View>
            ) : null}

            {!isProject ? (
              <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
              <Text style={[styles.sectionTitle, { color: textColor }]}>AI & recommendations</Text>

              {isUserAuthenticated ? (
                <View style={styles.premiumUnlockedWrap}>
                  <View style={[styles.premiumCard, { borderColor }]}>
                    <Text style={[styles.premiumLabel, { color: mutedColor }]}>Match score</Text>
                    <Text style={[styles.premiumScore, { color: textColor }]}>
                      {semanticScore !== null ? `${semanticScore}%` : 'N/A'}
                    </Text>
                  </View>

                  <View style={[styles.premiumCard, { borderColor }]}>
                    <Text style={[styles.premiumLabel, { color: mutedColor }]}>Why this matches</Text>
                    {matchBullets.map((bullet) => (
                      <Text key={bullet} style={[styles.bulletText, { color: textColor }]}>
                        - {bullet}
                      </Text>
                    ))}
                  </View>

                  <View style={[styles.premiumCard, { borderColor }]}>
                    <Text style={[styles.premiumLabel, { color: mutedColor }]}>Similar opportunities</Text>

                    {similarLoading ? (
                      <View style={styles.similarSkeletonWrap}>
                        <View
                          style={[
                            styles.similarSkeletonRow,
                            { borderColor, backgroundColor: `${tintColor}10` },
                          ]}
                        />
                        <View
                          style={[
                            styles.similarSkeletonRow,
                            { borderColor, backgroundColor: `${tintColor}10` },
                          ]}
                        />
                      </View>
                    ) : null}

                    {!similarLoading && similarError ? (
                      <Text style={[styles.sectionBody, { color: mutedColor }]}>{similarError}</Text>
                    ) : null}

                    {!similarLoading && !similarError && dedupedSimilar.length === 0 ? (
                      <Text style={[styles.sectionBody, { color: mutedColor }]}>
                        No similar opportunities.
                      </Text>
                    ) : null}

                    {!similarLoading && !similarError && dedupedSimilar.length > 0 ? (
                      <View style={styles.similarListWrap}>
                        {dedupedSimilar.map((similarItem) => {
                          const title =
                            String(similarItem.titre || '').trim() ||
                            `Opportunity #${similarItem.id}`;
                          const company =
                            String(similarItem.organisation_nom || '').trim() ||
                            'BidWise recommendation';
                          const score = Number(similarItem.similarity_score);
                          const scoreLabel = Number.isFinite(score)
                            ? `${Math.round(score * 100)}%`
                            : '--';

                          return (
                            <Pressable
                              key={similarItem.id}
                              accessibilityRole="button"
                              onPress={() => handleOpenSimilarOpportunity(similarItem.id)}
                              style={[styles.similarItemRow, { borderColor }]}
                            >
                              <Text
                                style={[styles.similarItemTitle, { color: textColor }]}
                                numberOfLines={2}
                              >
                                {title}
                              </Text>
                              <Text style={[styles.similarItemCompany, { color: mutedColor }]}>
                                {company}
                              </Text>
                              <Text style={[styles.similarItemScore, { color: tintColor }]}>
                                Match {scoreLabel}
                              </Text>
                            </Pressable>
                          );
                        })}
                      </View>
                    ) : null}
                  </View>
                </View>
              ) : (
                <View style={styles.premiumLockedWrap}>
                  <View style={[styles.premiumCard, { borderColor }]}>
                    <Text style={[styles.premiumLabel, { color: mutedColor }]}>Match score</Text>
                    <Text style={[styles.lockedValue, { color: textColor }]}>Locked</Text>
                  </View>

                  <View style={[styles.premiumCard, { borderColor }]}>
                    <Text style={[styles.premiumLabel, { color: mutedColor }]}>Why this matches</Text>
                    <Text style={[styles.sectionBody, { color: mutedColor }]}>
                      Profile fit explainer locked.
                    </Text>
                  </View>

                  <View style={[styles.premiumCard, { borderColor }]}>
                    <Text style={[styles.premiumLabel, { color: mutedColor }]}>
                      Similar opportunities
                    </Text>
                    <Text style={[styles.sectionBody, { color: mutedColor }]}>
                      Personalized ranking locked.
                    </Text>
                  </View>

                  <Pressable
                    accessibilityRole="button"
                    style={[styles.unlockButton, { backgroundColor: tintColor }]}
                    onPress={handleOpenLogin}
                  >
                    <Text style={styles.unlockButtonText}>Quick login</Text>
                  </Pressable>
                </View>
              )}
              </View>
            ) : null}
          </>
        ) : null}
      </ScrollView>

      <View
        style={[
          styles.stickyActionBar,
          {
            borderColor,
            backgroundColor: cardColor,
            paddingBottom: Math.max(insets.bottom, 16),
          },
        ]}
      >
        {isUserAuthenticated ? (
          <>
            <Pressable
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.stickySecondaryButton,
                { borderColor, opacity: pressed ? 0.9 : 1 },
              ]}
              onPress={handleSavePress}
            >
              <Text style={[styles.stickySecondaryButtonText, { color: textColor }]}>
                {isSaved ? 'Saved' : 'Save'}
              </Text>
            </Pressable>

            <Pressable
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.stickyPrimaryButton,
                {
                  backgroundColor: applyDisabled ? `${tintColor}55` : tintColor,
                  opacity: pressed ? 0.9 : 1,
                },
              ]}
              onPress={() => void handleApplyPress()}
              disabled={applyDisabled}
            >
              <Text style={styles.stickyPrimaryButtonText}>
                {isProject ? 'See on MarchesPublics.gov.tn' : 'Apply'}
              </Text>
            </Pressable>
          </>
        ) : (
          <>
            <Pressable
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.stickyPrimaryButton,
                { backgroundColor: tintColor, opacity: pressed ? 0.9 : 1 },
              ]}
              onPress={handleOpenLogin}
            >
              <Text style={styles.stickyPrimaryButtonText}>Quick login</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.stickySecondaryButton,
                { borderColor, opacity: pressed ? 0.9 : 1 },
              ]}
              onPress={handleOpenLogin}
            >
              <Text style={[styles.stickySecondaryButtonText, { color: textColor }]}>
                Unlock actions
              </Text>
            </Pressable>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  screen: {
    flexGrow: 1,
    paddingTop: 54,
    paddingHorizontal: 16,
  },
  topBar: {
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backText: {
    fontSize: 15,
    fontWeight: '700',
  },
  inlineLoginButton: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    minHeight: 36,
    justifyContent: 'center',
  },
  inlineLoginButtonText: {
    fontSize: 12,
    fontWeight: '800',
  },
  skeletonContainer: {
    gap: 12,
  },
  mainCard: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
  },
  sectionCard: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
  },
  guestLockStrip: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  guestLockStripTextWrap: {
    flex: 1,
  },
  guestLockStripTitle: {
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 2,
  },
  guestLockStripText: {
    fontSize: 12,
    lineHeight: 18,
  },
  guestLockStripButton: {
    minHeight: 42,
    borderRadius: 10,
    paddingHorizontal: 12,
    justifyContent: 'center',
  },
  guestLockStripButtonText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '800',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  headerContent: {
    flex: 1,
  },
  title: {
    fontSize: 18,
    lineHeight: 24,
    fontWeight: '800',
    marginBottom: 4,
  },
  companyText: {
    fontSize: 14,
  },
  chipRow: {
    flexDirection: 'row',
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
    fontWeight: '800',
  },
  metaText: {
    fontSize: 13,
    marginBottom: 6,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 10,
  },
  sectionBody: {
    fontSize: 13,
    lineHeight: 20,
  },
  scanGrid: {
    gap: 8,
  },
  factRow: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  factLabel: {
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 3,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  factValue: {
    fontSize: 14,
    fontWeight: '700',
  },
  inlineSection: {
    marginTop: 14,
  },
  inlineSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    marginBottom: 8,
  },
  inlineSectionTitle: {
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  inlineActionText: {
    fontSize: 13,
    fontWeight: '700',
  },
  skillsWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  skillChipText: {
    fontSize: 12,
    fontWeight: '700',
  },
  descriptionText: {
    fontSize: 14,
    lineHeight: 22,
  },
  premiumUnlockedWrap: {
    gap: 10,
  },
  premiumLockedWrap: {
    gap: 10,
  },
  premiumCard: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
  },
  premiumLabel: {
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  premiumScore: {
    fontSize: 28,
    fontWeight: '900',
  },
  lockedValue: {
    fontSize: 22,
    fontWeight: '900',
  },
  bulletText: {
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 3,
  },
  unlockButton: {
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    minHeight: 44,
    justifyContent: 'center',
  },
  unlockButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
    textAlign: 'center',
  },
  similarSkeletonWrap: {
    gap: 8,
  },
  similarSkeletonRow: {
    borderWidth: 1,
    borderRadius: 12,
    height: 52,
  },
  similarListWrap: {
    gap: 8,
  },
  similarItemRow: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  similarItemTitle: {
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 4,
  },
  similarItemCompany: {
    fontSize: 12,
    marginBottom: 4,
  },
  similarItemScore: {
    fontSize: 12,
    fontWeight: '800',
  },
  stickyActionBar: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 16,
  },
  stickyPrimaryButton: {
    flex: 1,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44,
  },
  stickyPrimaryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
  stickySecondaryButton: {
    flex: 1,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44,
  },
  stickySecondaryButtonText: {
    fontSize: 14,
    fontWeight: '800',
  },
  errorCard: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    marginTop: 24,
  },
  errorTitle: {
    fontSize: 18,
    fontWeight: '800',
    marginBottom: 8,
  },
  errorMessage: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 16,
  },
  retryButton: {
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
    minHeight: 42,
    justifyContent: 'center',
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
  skeletonBlock: {
    borderRadius: 8,
  },
});
