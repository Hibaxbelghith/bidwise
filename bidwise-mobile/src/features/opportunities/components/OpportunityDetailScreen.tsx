import { useCallback, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { getResumeDisplayName } from '@/src/features/profile/utils/resumeDisplay';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import { useOpportunityDetail } from '../hooks/useOpportunityDetail';
import {
  formatDate,
  formatExperienceLabel,
  formatProjectDocumentType,
  formatStatusLabel,
  formatTypeLabel,
} from '../utils/opportunityFormatters';
import {
  formatDisplayValue,
  getOpportunityMatchScorePercent,
  hasDisplayValue,
} from '../utils/opportunityHelpers';
import { toggleSavedOpportunity } from '../utils/savedOpportunitiesStorage';
import OpportunityAssistantSheet from './OpportunityAssistantSheet';
import OpportunityLogo from './OpportunityLogo';
import {
  registerExternalApplicationClick,
  submitOrganizationApplication,
  updateExternalApplicationStatus,
} from '../services/opportunitiesService';

const DESCRIPTION_LINES_COLLAPSED = 7;
const DIRECT_APPLICATION_STATUSES = new Set([
  'SUBMITTED',
  'VIEWED_BY_ORGANIZATION',
  'SHORTLISTED',
  'REJECTED',
  'WITHDRAWN',
  'EXTERNAL_APPLIED_CONFIRMED',
]);
const EXTERNAL_CONFIRMED_STATUS = 'EXTERNAL_APPLIED_CONFIRMED';
const EXTERNAL_REMIND_LATER_STATUS = 'EXTERNAL_REMIND_LATER';
const APPLIED_GREEN = '#16a34a';

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
  icon: _icon,
  label,
  mutedColor,
  textColor,
  value,
}: FactRowProps) {
  if (!value) return null;

  return (
    <View style={[styles.factRow, { borderColor }]}>
      <Text style={[styles.factLabel, { color: mutedColor }]}>{label}</Text>
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
  const { id, recommendationScore } = useLocalSearchParams<{
    id?: string | string[];
    recommendationScore?: string | string[];
  }>();
  const { isAuthenticated, loading: authLoading, user, loadUserProfile } = useAuth();
  const [applicationOpen, setApplicationOpen] = useState(false);
  const [contactPhone, setContactPhone] = useState('');
  const [submittingApplication, setSubmittingApplication] = useState(false);
  const [applicationError, setApplicationError] = useState('');
  const [assistantOpen, setAssistantOpen] = useState(false);

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
  const activeResume = user?.profil?.active_resume || null;
  const contactEmail = String(user?.email || user?.username || '').trim();
  const sourceName = String(sourceLabel || item?.source?.nom || '').trim();
  const sourceNameLower = sourceName.toLowerCase();
  const isMarchesPublicsSource = sourceNameLower.includes('marchespublics')
    || sourceNameLower.includes('marches publics')
    || sourceNameLower.includes('haicop');
  const acceptsDirectApplications = Boolean(item?.accepts_direct_applications) && !isProject;
  const applicationStatus = String(item?.my_application?.status || '').trim().toUpperCase();
  const hasApplication = DIRECT_APPLICATION_STATUSES.has(applicationStatus);
  const hasSourceUrl = Boolean(String(item?.source_item_url || '').trim());
  const applyDisabled = Boolean(
    isUserAuthenticated
      && (
        submittingApplication
        || hasApplication
        || (!acceptsDirectApplications && !hasSourceUrl)
        || (isProject && !hasSourceUrl)
      ),
  );
  const visibleSkills = showAllSkills ? skills : quickScanSkills;
  const showAssistantCta = isUserAuthenticated
    && !isProject
    && ['EMPLOI', 'STAGE'].includes(String(item?.type_opportunite || '').trim().toUpperCase());
  const passedRecommendationScore = useMemo(() => {
    const rawValue = Array.isArray(recommendationScore) ? recommendationScore[0] : recommendationScore;
    const parsed = Number(rawValue);
    return Number.isFinite(parsed) ? Math.max(0, Math.min(Math.round(parsed), 100)) : null;
  }, [recommendationScore]);
  const detailMatchScore = useMemo(() => {
    if (passedRecommendationScore !== null) return passedRecommendationScore;
    return item ? getOpportunityMatchScorePercent(item) : semanticScore;
  }, [item, passedRecommendationScore, semanticScore]);
  const showRecommendationInsight = Boolean(
    !isProject &&
      isUserAuthenticated &&
      detailMatchScore !== null &&
      passedRecommendationScore !== null,
  );
  const resumeLabel = useMemo(() => {
    return getResumeDisplayName(activeResume, 'Active profile resume');
  }, [activeResume]);

  const primaryActionLabel = useMemo(() => {
    if (hasApplication) return 'Applied';
    if (isProject) {
      if (isMarchesPublicsSource) return 'See on MarchesPublics.gov.tn';
      return hasSourceUrl ? 'Open source' : 'No online submission';
    }
    if (acceptsDirectApplications) return 'Apply';
    return 'Open source';
  }, [acceptsDirectApplications, hasApplication, hasSourceUrl, isMarchesPublicsSource, isProject]);

  const getApplicationErrorMessage = useCallback((errorValue: any) => {
    const data = errorValue?.response?.data;
    if (errorValue?.response?.status === 409) return 'You have already applied for this opportunity.';
    if (data?.cv_id?.[0]) return 'Select a resume from your profile before applying.';
    if (data?.contact_email?.[0]) return data.contact_email[0];
    if (data?.contact_phone?.[0]) return data.contact_phone[0];
    if (data?.cover_letter_url?.[0]) return data.cover_letter_url[0];
    return data?.detail || 'Unable to submit your application.';
  }, []);

  const updateExternalStatus = useCallback(
    async (applicationId: unknown, status: string) => {
      const parsedApplicationId = Number(applicationId);
      if (!Number.isInteger(parsedApplicationId) || parsedApplicationId <= 0) return;

      try {
        await updateExternalApplicationStatus(parsedApplicationId, status);
        await Promise.allSettled([fetchDetail(), loadUserProfile()]);
      } catch {
        Alert.alert(
          'Unable to update application',
          'BidWise could not update your external application status right now.',
        );
      }
    },
    [fetchDetail, loadUserProfile],
  );

  const showExternalApplicationPrompt = useCallback(
    (applicationId: unknown) => {
      Alert.alert(
        'Did you apply?',
        'BidWise opened the employer page. Tell us whether you completed the application so your dashboard stays up to date.',
        [
          {
            text: 'No, not yet',
            style: 'cancel',
          },
          {
            text: 'Remind me later',
            onPress: () => void updateExternalStatus(applicationId, EXTERNAL_REMIND_LATER_STATUS),
          },
          {
            text: 'Yes, I applied',
            onPress: () => void updateExternalStatus(applicationId, EXTERNAL_CONFIRMED_STATUS),
          },
        ],
      );
    },
    [updateExternalStatus],
  );

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

  const handleOpenSource = useCallback(async () => {
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
      if (!isProject && item?.id && !acceptsDirectApplications) {
        try {
          const result = await registerExternalApplicationClick(item.id);
          await fetchDetail();
          showExternalApplicationPrompt(result.application_id);
        } catch {
          Alert.alert(
            'Tracking unavailable',
            'The source was opened, but BidWise could not start external application tracking.',
          );
        }
      }
    } catch {
      Alert.alert('Source unavailable', 'Failed to open this source link.');
    }
  }, [
    acceptsDirectApplications,
    fetchDetail,
    isProject,
    item?.id,
    item?.source_item_url,
    showExternalApplicationPrompt,
  ]);

  const handleApplyPress = useCallback(async () => {
    if (!isUserAuthenticated) {
      handleOpenLogin();
      return;
    }

    if (hasApplication) {
      Alert.alert('Already submitted', 'Your application is already recorded for this opportunity.');
      return;
    }

    if (!acceptsDirectApplications) {
      await handleOpenSource();
      return;
    }

    if (!activeResume?.id) {
      Alert.alert(
        'Resume required',
        'Upload or activate a resume in your profile before applying.',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Open profile', onPress: () => router.push('/profile-resume') },
        ],
      );
      return;
    }

    setApplicationError('');
    setContactPhone('');
    setApplicationOpen(true);
  }, [
    acceptsDirectApplications,
    activeResume?.id,
    handleOpenLogin,
    handleOpenSource,
    hasApplication,
    isUserAuthenticated,
    router,
  ]);

  const handleSubmitApplication = useCallback(async () => {
    if (!item?.id || !activeResume?.id) return;
    if (!contactEmail) {
      setApplicationError('Your account email is required before applying.');
      return;
    }

    try {
      setApplicationError('');
      setSubmittingApplication(true);
      await submitOrganizationApplication(item.id, {
        cv_id: activeResume.id,
        cover_letter_url: '',
        contact_email: contactEmail,
        contact_phone: contactPhone.trim(),
      });
      setApplicationOpen(false);
      setContactPhone('');
      await Promise.allSettled([fetchDetail(), loadUserProfile()]);
      Alert.alert('Application submitted', 'Your application was sent successfully.');
    } catch (submitError: any) {
      setApplicationError(getApplicationErrorMessage(submitError));
    } finally {
      setSubmittingApplication(false);
    }
  }, [
    activeResume?.id,
    contactEmail,
    contactPhone,
    fetchDetail,
    getApplicationErrorMessage,
    item?.id,
    loadUserProfile,
  ]);

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
    <SafeAreaView edges={['top']} style={[styles.root, { backgroundColor }]}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[
          styles.screen,
          {
            backgroundColor,
            paddingTop: 18,
            paddingBottom: 188 + Math.max(insets.bottom, 28),
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
                  sourceName={sourceLabel || (isProject ? 'MarchesPublics' : '')}
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
                {showRecommendationInsight && detailMatchScore !== null ? (
                  <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}14` }]}>
                    <Text style={[styles.chipText, { color: tintColor }]}>
                      Match {detailMatchScore}%
                    </Text>
                  </View>
                ) : null}
              </View>

              {showAssistantCta ? (
                <Pressable
                  accessibilityRole="button"
                  onPress={() => setAssistantOpen(true)}
                  style={({ pressed }) => [
                    styles.assistantCta,
                    {
                      borderColor: tintColor,
                      backgroundColor: tintColor,
                      opacity: pressed ? 0.88 : 1,
                    },
                  ]}
                >
                  <View style={styles.assistantCtaRow}>
                    <View style={styles.assistantCtaBadge}>
                      <Text style={[styles.assistantCtaBadgeText, { color: tintColor }]}>AI</Text>
                    </View>
                    <View style={styles.assistantCtaCopy}>
                      <Text style={styles.assistantCtaEyebrow}>BidWise AI assistant</Text>
                      <Text style={styles.assistantCtaText}>
                        Is your resume a good match?
                      </Text>
                    </View>
                  </View>
                </Pressable>
              ) : null}

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

            {showRecommendationInsight ? (
              <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
              <Text style={[styles.sectionTitle, { color: textColor }]}>AI & recommendations</Text>

              {isUserAuthenticated ? (
                <View style={styles.premiumUnlockedWrap}>
                  <View style={[styles.premiumCard, { borderColor }]}>
                    <Text style={[styles.premiumLabel, { color: mutedColor }]}>Match score</Text>
                    <Text style={[styles.premiumScore, { color: textColor }]}>
                      {detailMatchScore !== null ? `${detailMatchScore}%` : 'N/A'}
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

            {!isProject ? (
              <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}>
                <Text style={[styles.sectionTitle, { color: textColor }]}>Similar opportunities</Text>

                {!isUserAuthenticated ? (
                  <Text style={[styles.sectionBody, { color: mutedColor }]}>
                    Login to view similar opportunities.
                  </Text>
                ) : null}

                {isUserAuthenticated && similarLoading ? (
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

                {isUserAuthenticated && !similarLoading && similarError ? (
                  <Text style={[styles.sectionBody, { color: mutedColor }]}>
                    Similar opportunities are currently unavailable.
                  </Text>
                ) : null}

                {isUserAuthenticated && !similarLoading && !similarError && dedupedSimilar.length === 0 ? (
                  <Text style={[styles.sectionBody, { color: mutedColor }]}>
                    No similar opportunities found.
                  </Text>
                ) : null}

                {isUserAuthenticated && !similarLoading && !similarError && dedupedSimilar.length > 0 ? (
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
                  backgroundColor: hasApplication
                    ? APPLIED_GREEN
                    : applyDisabled
                      ? `${tintColor}55`
                      : tintColor,
                  opacity: pressed ? 0.9 : 1,
                },
              ]}
              onPress={() => void handleApplyPress()}
              disabled={applyDisabled}
            >
              <Text style={styles.stickyPrimaryButtonText}>
                {primaryActionLabel}
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

      <Modal
        visible={applicationOpen}
        transparent
        animationType="slide"
        onRequestClose={() => {
          if (!submittingApplication) setApplicationOpen(false);
        }}
      >
        <View style={styles.modalOverlay}>
          <View
            style={[
              styles.applicationSheet,
              {
                backgroundColor: cardColor,
                borderColor,
                paddingBottom: Math.max(insets.bottom + 24, 34),
              },
            ]}
          >
            <View style={styles.applicationHeader}>
              <View style={styles.applicationHeaderText}>
                <Text style={[styles.applicationTitle, { color: textColor }]}>Apply to this opportunity</Text>
                <Text style={[styles.applicationSubtitle, { color: mutedColor }]} numberOfLines={2}>
                  {companyLabel || 'Organization'} reviews applications from BidWise.
                </Text>
              </View>
              <Pressable
                accessibilityRole="button"
                disabled={submittingApplication}
                onPress={() => setApplicationOpen(false)}
                style={({ pressed }) => [
                  styles.applicationCloseButton,
                  { borderColor, opacity: pressed ? 0.8 : 1 },
                ]}
              >
                <Text style={[styles.applicationCloseText, { color: mutedColor }]}>Close</Text>
              </Pressable>
            </View>

            <View style={[styles.applicationInfoBox, { borderColor }]}>
              <Text style={[styles.applicationInfoLabel, { color: mutedColor }]}>Resume</Text>
              <Text style={[styles.applicationInfoValue, { color: textColor }]} numberOfLines={1}>
                {resumeLabel}
              </Text>
            </View>

            <View style={[styles.applicationInfoBox, { borderColor }]}>
              <Text style={[styles.applicationInfoLabel, { color: mutedColor }]}>Contact email</Text>
              <Text style={[styles.applicationInfoValue, { color: textColor }]} numberOfLines={1}>
                {contactEmail || 'Missing account email'}
              </Text>
            </View>

            <View style={styles.applicationField}>
              <Text style={[styles.applicationInfoLabel, { color: mutedColor }]}>
                Phone number <Text style={styles.optionalText}>(optional)</Text>
              </Text>
              <TextInput
                value={contactPhone}
                onChangeText={setContactPhone}
                placeholder="+21612345678"
                placeholderTextColor={mutedColor}
                keyboardType="phone-pad"
                editable={!submittingApplication}
                style={[
                  styles.applicationInput,
                  {
                    borderColor,
                    color: textColor,
                    backgroundColor,
                  },
                ]}
              />
            </View>

            {applicationError ? (
              <View style={styles.applicationErrorBox}>
                <Text style={styles.applicationErrorText}>{applicationError}</Text>
              </View>
            ) : null}

            <View style={styles.applicationActions}>
              <Pressable
                accessibilityRole="button"
                disabled={submittingApplication}
                onPress={() => setApplicationOpen(false)}
                style={({ pressed }) => [
                  styles.applicationSecondaryButton,
                  { borderColor, opacity: pressed ? 0.85 : 1 },
                ]}
              >
                <Text style={[styles.applicationSecondaryText, { color: textColor }]}>Cancel</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                disabled={submittingApplication}
                onPress={() => void handleSubmitApplication()}
                style={({ pressed }) => [
                  styles.applicationPrimaryButton,
                  {
                    backgroundColor: tintColor,
                    opacity: pressed || submittingApplication ? 0.85 : 1,
                  },
                ]}
              >
                {submittingApplication ? (
                  <ActivityIndicator color="#ffffff" />
                ) : (
                  <Text style={styles.applicationPrimaryText}>Submit application</Text>
                )}
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>

      <OpportunityAssistantSheet
        opportunityId={item?.id || null}
        visible={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        colors={{
          background: backgroundColor,
          card: cardColor,
          border: borderColor,
          text: textColor,
          muted: mutedColor,
          tint: tintColor,
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  screen: {
    flexGrow: 1,
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
  assistantCta: {
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 13,
    marginBottom: 10,
  },
  assistantCtaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  assistantCtaBadge: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  assistantCtaBadgeText: {
    fontSize: 13,
    fontWeight: '900',
  },
  assistantCtaCopy: {
    flex: 1,
  },
  assistantCtaEyebrow: {
    color: 'rgba(255,255,255,0.78)',
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
    marginBottom: 3,
  },
  assistantCtaText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '900',
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
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(15, 23, 42, 0.45)',
  },
  applicationSheet: {
    borderTopWidth: 1,
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    paddingHorizontal: 18,
    paddingTop: 18,
    paddingBottom: 24,
    gap: 12,
  },
  applicationHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  applicationHeaderText: {
    flex: 1,
  },
  applicationTitle: {
    fontSize: 18,
    fontWeight: '900',
    marginBottom: 4,
  },
  applicationSubtitle: {
    fontSize: 13,
    lineHeight: 19,
  },
  applicationCloseButton: {
    borderWidth: 1,
    borderRadius: 999,
    minHeight: 34,
    paddingHorizontal: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  applicationCloseText: {
    fontSize: 12,
    fontWeight: '800',
  },
  applicationInfoBox: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  applicationInfoLabel: {
    fontSize: 12,
    fontWeight: '800',
    marginBottom: 6,
    textTransform: 'uppercase',
  },
  applicationInfoValue: {
    fontSize: 14,
    fontWeight: '700',
  },
  applicationField: {
    gap: 4,
  },
  optionalText: {
    color: '#71717a',
    fontWeight: '700',
    textTransform: 'none',
  },
  applicationInput: {
    borderWidth: 1,
    borderRadius: 12,
    minHeight: 46,
    paddingHorizontal: 12,
    fontSize: 15,
    fontWeight: '700',
  },
  applicationErrorBox: {
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#fef2f2',
  },
  applicationErrorText: {
    color: '#b91c1c',
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 18,
  },
  applicationActions: {
    flexDirection: 'row',
    gap: 10,
    paddingTop: 4,
  },
  applicationSecondaryButton: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 12,
    minHeight: 46,
    alignItems: 'center',
    justifyContent: 'center',
  },
  applicationSecondaryText: {
    fontSize: 14,
    fontWeight: '800',
  },
  applicationPrimaryButton: {
    flex: 1.3,
    borderRadius: 12,
    minHeight: 46,
    alignItems: 'center',
    justifyContent: 'center',
  },
  applicationPrimaryText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '900',
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
