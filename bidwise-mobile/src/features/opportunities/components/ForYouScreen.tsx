import { Ionicons } from '@expo/vector-icons';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import type { ProfileUser } from '@/src/features/profile/types';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import { useForYouFeed } from '../hooks/useForYouFeed';
import { getRecommendationScorePercent } from '../utils/recommendationUtils';
import ForYouOpportunityCard from './ForYouOpportunityCard';


function StateCard({
  icon,
  title,
  description,
  textColor,
  mutedColor,
  borderColor,
  cardColor,
  primaryLabel,
  primaryAction,
  primaryBackground,
  secondaryLabel,
  secondaryAction,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  description: string;
  textColor: string;
  mutedColor: string;
  borderColor: string;
  cardColor: string;
  primaryLabel?: string;
  primaryAction?: () => void;
  primaryBackground: string;
  secondaryLabel?: string;
  secondaryAction?: () => void;
}) {
  return (
    <View style={[styles.stateCard, { backgroundColor: cardColor, borderColor }]}>
      <View style={[styles.stateIconWrap, { borderColor }]}>
        <Ionicons name={icon} size={18} color={textColor} />
      </View>
      <Text style={[styles.stateTitle, { color: textColor }]}>{title}</Text>
      <Text style={[styles.stateDescription, { color: mutedColor }]}>{description}</Text>

      <View style={styles.stateActions}>
        {primaryLabel && primaryAction ? (
          <Pressable
            accessibilityRole="button"
            style={[styles.primaryActionButton, { backgroundColor: primaryBackground }]}
            onPress={primaryAction}
          >
            <Text style={styles.primaryActionText}>{primaryLabel}</Text>
          </Pressable>
        ) : null}

        {secondaryLabel && secondaryAction ? (
          <Pressable
            accessibilityRole="button"
            style={[styles.secondaryActionButton, { borderColor }]}
            onPress={secondaryAction}
          >
            <Text style={[styles.secondaryActionText, { color: textColor }]}>
              {secondaryLabel}
            </Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

function getForYouDetailParams(item: any) {
  const recommendation = item?.recommendation || item;
  const scorePercent = getRecommendationScorePercent(
    recommendation?.score ?? recommendation?.match_score,
  );

  return {
    id: String(item.id),
    recommendationScore: scorePercent !== null ? String(scorePercent) : undefined,
  };
}

function RecommendationSkeleton({
  cardColor,
  borderColor,
  skeletonBase,
  skeletonSoft,
}: {
  cardColor: string;
  borderColor: string;
  skeletonBase: string;
  skeletonSoft: string;
}) {
  return (
    <View style={[styles.skeletonCard, { backgroundColor: cardColor, borderColor }]}>
      <View style={styles.skeletonHeader}>
        <View style={[styles.skeletonPill, { width: 96, backgroundColor: skeletonSoft }]} />
        <View style={[styles.skeletonScore, { backgroundColor: skeletonSoft }]} />
      </View>
      <View style={styles.skeletonBody}>
        <View style={[styles.skeletonLogo, { backgroundColor: skeletonBase }]} />
        <View style={styles.skeletonHeaderText}>
          <View style={[styles.skeletonLine, { width: '88%', backgroundColor: skeletonBase }]} />
          <View style={[styles.skeletonLine, { width: '52%', backgroundColor: skeletonSoft }]} />
        </View>
      </View>
      <View style={[styles.skeletonLine, { width: '78%', backgroundColor: skeletonBase }]} />
      <View style={[styles.skeletonLine, { width: '68%', backgroundColor: skeletonSoft }]} />
      <View style={styles.skeletonFooter}>
        <View style={[styles.skeletonPill, { width: 70, backgroundColor: skeletonSoft }]} />
        <View style={[styles.skeletonPill, { width: 84, backgroundColor: skeletonSoft }]} />
        <View style={[styles.skeletonPill, { width: 60, backgroundColor: skeletonSoft }]} />
      </View>
    </View>
  );
}

type ForYouScreenProps = {
  embedded?: boolean;
};

export default function ForYouScreen({ embedded = false }: ForYouScreenProps) {
  const router = useRouter();
  const { isAuthenticated, loading: authLoading, user } = useAuth();
  const typedUser = user as ProfileUser | null;

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');
  const skeletonBase = useThemeColor({ light: '#d4d4d8', dark: '#2f2f2f' }, 'border');
  const skeletonSoft = useThemeColor({ light: '#e4e4e7', dark: '#3a3a3a' }, 'card');

  const {
    strongMatches,
    relatedOpportunities,
    loading,
    refreshing,
    error,
    profileTier,
    isColdProfile,
    isTenderOnlyProfile,
    handleRefresh,
  } = useForYouFeed({
    ready: !authLoading,
    isAuthenticated,
    user: typedUser,
  });

  const qualifiedCount = strongMatches.length + relatedOpportunities.length;
  const showLoading = authLoading || loading;
  const showGuestState = !authLoading && !isAuthenticated;
  const showIncompleteProfile = isAuthenticated && profileTier === 'insufficient' && !showLoading && !error;
  const showColdState =
    isAuthenticated &&
    profileTier !== 'insufficient' &&
    isColdProfile &&
    qualifiedCount === 0 &&
    !showLoading &&
    !error;
  const showEmptyState =
    isAuthenticated &&
    !showIncompleteProfile &&
    !showColdState &&
    qualifiedCount === 0 &&
    !showLoading &&
    !error;
  const showResults = isAuthenticated && qualifiedCount > 0 && !error;
  const isPartialProfile = isAuthenticated && !isTenderOnlyProfile && profileTier === 'partial';
  const primaryMetricLabel = isTenderOnlyProfile ? 'Strong priorities' : 'Strong matches';
  const secondaryMetricLabel = isTenderOnlyProfile ? 'To review' : 'Review next';
  const signalMetricLabel = isTenderOnlyProfile ? 'Tender profile' : 'Profile signal';
  const incompleteTitle = isTenderOnlyProfile
    ? 'Complete tender preferences'
    : 'Complete your profile to unlock For You';
  const incompleteDescription = isTenderOnlyProfile
    ? 'Choose at least one region and tender category so BidWise can rank active calls for tender.'
    : 'Add roles, preferences, skills, or a CV so BidWise can rank opportunities with stronger signals.';
  const emptyTitle = isTenderOnlyProfile ? 'No tender priorities yet' : 'No strong recommendations yet';
  const emptyDescription = isTenderOnlyProfile
    ? 'BidWise did not find enough active tenders for your selected categories and regions right now.'
    : 'BidWise did not find enough qualified matches right now. You can still explore all active opportunities.';

  return (
    <View style={[styles.root, { backgroundColor }]}>
      <ScrollView
        contentContainerStyle={[styles.content, { paddingTop: embedded ? 16 : 20 }]}
        refreshControl={
          isAuthenticated ? (
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor={tintColor}
              colors={[tintColor]}
            />
          ) : undefined
        }
        showsVerticalScrollIndicator={false}
      >

        {showResults ? (
          <View style={styles.kpiRow}>
            <View style={[styles.kpiCard, { backgroundColor: cardColor, borderColor }]}>
              <Text style={[styles.kpiValue, { color: textColor }]}>{strongMatches.length}</Text>
              <Text style={[styles.kpiLabel, { color: mutedColor }]}>{primaryMetricLabel}</Text>
            </View>
            <View style={[styles.kpiCard, { backgroundColor: cardColor, borderColor }]}>
              <Text style={[styles.kpiValue, { color: textColor }]}>{relatedOpportunities.length}</Text>
              <Text style={[styles.kpiLabel, { color: mutedColor }]}>{secondaryMetricLabel}</Text>
            </View>
            <View style={[styles.kpiCard, { backgroundColor: cardColor, borderColor }]}>
              <Text style={[styles.kpiValue, { color: textColor }]}>{isPartialProfile ? 'Partial' : 'Ready'}</Text>
              <Text style={[styles.kpiLabel, { color: mutedColor }]}>{signalMetricLabel}</Text>
            </View>
          </View>
        ) : null}

        {isPartialProfile && showResults ? (
          <View style={[styles.infoBanner, { backgroundColor: cardColor, borderColor }]}>
            <View style={styles.infoBannerHeader}>
              <Ionicons name="information-circle-outline" size={16} color={tintColor} />
              <Text style={[styles.infoBannerTitle, { color: textColor }]}>Recommendations can still improve</Text>
            </View>
            <Text style={[styles.infoBannerText, { color: mutedColor }]}>
              Add more profile details or update your CV to improve ranking precision and unlock stronger evidence.
            </Text>
          </View>
        ) : null}

        {showLoading ? (
          <View style={styles.loadingWrap}>
            {!authLoading ? (
              <>
                <RecommendationSkeleton
                  cardColor={cardColor}
                  borderColor={borderColor}
                  skeletonBase={skeletonBase}
                  skeletonSoft={skeletonSoft}
                />
                <RecommendationSkeleton
                  cardColor={cardColor}
                  borderColor={borderColor}
                  skeletonBase={skeletonBase}
                  skeletonSoft={skeletonSoft}
                />
                <RecommendationSkeleton
                  cardColor={cardColor}
                  borderColor={borderColor}
                  skeletonBase={skeletonBase}
                  skeletonSoft={skeletonSoft}
                />
              </>
            ) : (
              <View style={styles.centeredLoader}>
                <ActivityIndicator size="large" color={tintColor} />
              </View>
            )}
          </View>
        ) : null}

        {!showLoading && error ? (
          <StateCard
            icon="sync-outline"
            title="Recommendations are taking longer than expected"
            description="Your personalized feed is still syncing. You can retry now or keep browsing active opportunities."
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
            primaryLabel="Retry"
            primaryAction={handleRefresh}
            primaryBackground={tintColor}
            secondaryLabel="Explore opportunities"
            secondaryAction={() => router.push('/explore')}
          />
        ) : null}

        {showGuestState ? (
          <StateCard
            icon="person-circle-outline"
            title="Login to unlock For You"
            description="BidWise can rank opportunities for you using your profile, preferences, and CV."
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
            primaryLabel="Quick login"
            primaryAction={() => router.push('/login')}
            primaryBackground={tintColor}
            secondaryLabel="Browse all opportunities"
            secondaryAction={() => router.push('/explore')}
          />
        ) : null}

        {showIncompleteProfile ? (
          <StateCard
            icon="document-text-outline"
            title={incompleteTitle}
            description={incompleteDescription}
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
            primaryLabel="Complete profile"
            primaryAction={() => router.push('/profile')}
            primaryBackground={tintColor}
            secondaryLabel="Explore opportunities"
            secondaryAction={() => router.push('/explore')}
          />
        ) : null}

        {showColdState ? (
          <StateCard
            icon="sparkles-outline"
            title="Your recommendations are being prepared"
            description="Check back in a moment. BidWise is still preparing your personalized ranking after your recent profile or CV updates."
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
            primaryLabel="Refresh"
            primaryAction={handleRefresh}
            primaryBackground={tintColor}
            secondaryLabel="Explore opportunities"
            secondaryAction={() => router.push('/explore')}
          />
        ) : null}

        {showEmptyState ? (
          <StateCard
            icon="search-outline"
            title={emptyTitle}
            description={emptyDescription}
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
            primaryLabel="Explore opportunities"
            primaryAction={() => router.push('/explore')}
            primaryBackground={tintColor}
            secondaryLabel="Update profile"
            secondaryAction={() => router.push('/profile')}
          />
        ) : null}

        {showResults ? (
          <View style={styles.sectionsWrap}>
            {strongMatches.length ? (
              <View style={styles.section}>
                <View style={styles.sectionHeader}>
                  <Text style={[styles.sectionTitle, { color: textColor }]}>
                    {isTenderOnlyProfile ? 'Strong priorities' : 'Strong matches'}
                  </Text>
                  <Text style={[styles.sectionCount, { color: tintColor }]}>{strongMatches.length}</Text>
                </View>
                <Text style={[styles.sectionDescription, { color: mutedColor }]}>
                  {isTenderOnlyProfile
                    ? 'Best aligned with your tender categories, regions, and project context.'
                    : 'Best aligned with your role, skills, CV, and preferences.'}
                </Text>
                <View style={styles.cardList}>
                  {strongMatches.map((item) => (
                    <ForYouOpportunityCard
                      key={`strong-${item.id}`}
                      item={item}
                      onPress={() =>
                        router.push({
                          pathname: '/opportunities/[id]',
                          params: getForYouDetailParams(item),
                        })
                      }
                    />
                  ))}
                </View>
              </View>
            ) : null}

            {relatedOpportunities.length ? (
              <View style={styles.section}>
                <View style={styles.sectionHeader}>
                  <Text style={[styles.sectionTitle, { color: textColor }]}>
                    {isTenderOnlyProfile
                      ? 'Tenders to monitor'
                      : strongMatches.length
                        ? 'More opportunities for you'
                        : 'Recommended for review'}
                  </Text>
                  <Text style={[styles.sectionCount, { color: tintColor }]}>{relatedOpportunities.length}</Text>
                </View>
                <Text style={[styles.sectionDescription, { color: mutedColor }]}>
                  {isTenderOnlyProfile
                    ? 'Relevant tenders kept separate because they need manual review before action.'
                    : 'Lower-confidence opportunities that still match important parts of your profile.'}
                </Text>
                <View style={styles.cardList}>
                  {relatedOpportunities.map((item) => (
                    <ForYouOpportunityCard
                      key={`related-${item.id}`}
                      item={item}
                      onPress={() =>
                        router.push({
                          pathname: '/opportunities/[id]',
                          params: getForYouDetailParams(item),
                        })
                      }
                    />
                  ))}
                </View>
              </View>
            ) : null}
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 16,
    paddingBottom: 112,
    gap: 16,
  },
  kpiRow: {
    flexDirection: 'row',
    gap: 10,
  },
  kpiCard: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 16,
    paddingVertical: 14,
    paddingHorizontal: 12,
    alignItems: 'center',
    gap: 4,
  },
  kpiValue: {
    fontSize: 18,
    fontWeight: '700',
  },
  kpiLabel: {
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
  },
  infoBanner: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    gap: 6,
  },
  infoBannerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  infoBannerTitle: {
    fontSize: 14,
    fontWeight: '700',
  },
  infoBannerText: {
    fontSize: 13,
    lineHeight: 19,
  },
  loadingWrap: {
    gap: 12,
  },
  centeredLoader: {
    paddingVertical: 60,
    alignItems: 'center',
    justifyContent: 'center',
  },
  skeletonCard: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    gap: 12,
  },
  skeletonHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  skeletonPill: {
    height: 24,
    borderRadius: 999,
  },
  skeletonBody: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  skeletonLogo: {
    width: 50,
    height: 50,
    borderRadius: 14,
  },
  skeletonHeaderText: {
    flex: 1,
    gap: 8,
  },
  skeletonScore: {
    width: 60,
    height: 44,
    borderRadius: 12,
  },
  skeletonLine: {
    height: 12,
    borderRadius: 8,
  },
  skeletonFooter: {
    flexDirection: 'row',
    gap: 8,
  },
  stateCard: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 20,
    alignItems: 'center',
  },
  stateIconWrap: {
    width: 42,
    height: 42,
    borderRadius: 999,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  stateTitle: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 8,
    textAlign: 'center',
  },
  stateDescription: {
    fontSize: 14,
    lineHeight: 21,
    textAlign: 'center',
  },
  stateActions: {
    marginTop: 18,
    gap: 10,
    width: '100%',
  },
  primaryActionButton: {
    borderRadius: 12,
    minHeight: 46,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  primaryActionText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  secondaryActionButton: {
    borderWidth: 1,
    borderRadius: 12,
    minHeight: 46,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  secondaryActionText: {
    fontSize: 14,
    fontWeight: '700',
  },
  sectionsWrap: {
    gap: 22,
  },
  section: {
    gap: 10,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  sectionTitle: {
    flex: 1,
    fontSize: 20,
    fontWeight: '700',
  },
  sectionCount: {
    fontSize: 13,
    fontWeight: '700',
  },
  sectionDescription: {
    fontSize: 13,
    lineHeight: 19,
  },
  cardList: {
    gap: 12,
  },
});
