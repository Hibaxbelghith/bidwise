import { useMemo } from 'react';
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
import ForYouOpportunityCard from './ForYouOpportunityCard';

function StateCard({
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
        <View style={[styles.skeletonLogo, { backgroundColor: skeletonBase }]} />
        <View style={styles.skeletonHeaderText}>
          <View style={[styles.skeletonLine, { width: '88%', backgroundColor: skeletonBase }]} />
          <View style={[styles.skeletonLine, { width: '52%', backgroundColor: skeletonSoft }]} />
        </View>
        <View style={[styles.skeletonScore, { backgroundColor: skeletonSoft }]} />
      </View>
      <View style={[styles.skeletonLine, { width: '42%', backgroundColor: skeletonSoft }]} />
      <View style={[styles.skeletonLine, { width: '75%', backgroundColor: skeletonBase }]} />
      <View style={[styles.skeletonLine, { width: '68%', backgroundColor: skeletonSoft }]} />
    </View>
  );
}

export default function ForYouScreen() {
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
  const isPartialProfile = isAuthenticated && profileTier === 'partial';

  const recommendationSummary = useMemo(() => {
    if (!showResults) return '';
    if (strongMatches.length && relatedOpportunities.length) {
      return `${strongMatches.length} strong match${strongMatches.length > 1 ? 'es' : ''} and ${relatedOpportunities.length} related opportunit${relatedOpportunities.length > 1 ? 'ies' : 'y'}.`;
    }
    if (strongMatches.length) {
      return `${strongMatches.length} strong match${strongMatches.length > 1 ? 'es' : ''} ready to review.`;
    }
    return `${relatedOpportunities.length} related opportunit${relatedOpportunities.length > 1 ? 'ies' : 'y'} for you.`;
  }, [relatedOpportunities.length, showResults, strongMatches.length]);

  return (
    <View style={[styles.root, { backgroundColor }]}>
      <ScrollView
        contentContainerStyle={styles.content}
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
        <View style={styles.header}>
          <View style={styles.headerTextWrap}>
            <Text style={[styles.eyebrow, { color: tintColor }]}>Personalized feed</Text>
            <Text style={[styles.title, { color: textColor }]}>For You</Text>
            <Text style={[styles.subtitle, { color: mutedColor }]}>
              {showResults
                ? recommendationSummary
                : 'Recommended opportunities based on your profile, CV, and preferences.'}
            </Text>
          </View>

          <Pressable
            accessibilityRole="button"
            style={[styles.exploreButton, { borderColor }]}
            onPress={() => router.push('/opportunities')}
          >
            <Text style={[styles.exploreButtonText, { color: textColor }]}>Explore</Text>
          </Pressable>
        </View>

        {isPartialProfile && showResults ? (
          <View style={[styles.infoBanner, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.infoBannerTitle, { color: textColor }]}>Profile can be stronger</Text>
            <Text style={[styles.infoBannerText, { color: mutedColor }]}>
              These recommendations already use your best signals. Add more profile details or update
              your CV to improve ranking precision.
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
            title="Unable to load recommendations"
            description={error}
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
            primaryLabel="Retry"
            primaryAction={handleRefresh}
            primaryBackground={tintColor}
            secondaryLabel="Explore opportunities"
            secondaryAction={() => router.push('/opportunities')}
          />
        ) : null}

        {showGuestState ? (
          <StateCard
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
            secondaryAction={() => router.push('/opportunities')}
          />
        ) : null}

        {showIncompleteProfile ? (
          <StateCard
            title="Complete your profile to unlock For You"
            description="Add more roles, preferences, skills, or a CV so BidWise can rank opportunities with stronger signals."
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
            primaryLabel="Complete profile"
            primaryAction={() => router.push('/profile')}
            primaryBackground={tintColor}
            secondaryLabel="Explore opportunities"
            secondaryAction={() => router.push('/opportunities')}
          />
        ) : null}

        {showColdState ? (
          <StateCard
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
            secondaryAction={() => router.push('/opportunities')}
          />
        ) : null}

        {showEmptyState ? (
          <StateCard
            title="No strong recommendations yet"
            description="BidWise did not find enough qualified matches right now. You can still explore all active opportunities."
            textColor={textColor}
            mutedColor={mutedColor}
            borderColor={borderColor}
            cardColor={cardColor}
            primaryLabel="Explore opportunities"
            primaryAction={() => router.push('/opportunities')}
            primaryBackground={tintColor}
            secondaryLabel="Update profile"
            secondaryAction={() => router.push('/profile')}
          />
        ) : null}

        {showResults ? (
          <View style={styles.sectionsWrap}>
            {strongMatches.length ? (
              <View style={styles.section}>
                <Text style={[styles.sectionTitle, { color: textColor }]}>Strong matches</Text>
                <Text style={[styles.sectionDescription, { color: mutedColor }]}>
                  Best aligned with your role, skills, CV, and preferences.
                </Text>
                <View style={styles.cardList}>
                  {strongMatches.map((item) => (
                    <ForYouOpportunityCard
                      key={`strong-${item.id}`}
                      item={item}
                      onPress={() =>
                        router.push({
                          pathname: '/opportunities/[id]',
                          params: { id: String(item.id) },
                        })
                      }
                    />
                  ))}
                </View>
              </View>
            ) : null}

            {relatedOpportunities.length ? (
              <View style={styles.section}>
                <Text style={[styles.sectionTitle, { color: textColor }]}>
                  {strongMatches.length ? 'More opportunities for you' : 'Recommended for review'}
                </Text>
                <Text style={[styles.sectionDescription, { color: mutedColor }]}>
                  Lower-confidence opportunities that still match important parts of your profile.
                </Text>
                <View style={styles.cardList}>
                  {relatedOpportunities.map((item) => (
                    <ForYouOpportunityCard
                      key={`related-${item.id}`}
                      item={item}
                      onPress={() =>
                        router.push({
                          pathname: '/opportunities/[id]',
                          params: { id: String(item.id) },
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
    paddingTop: 56,
    paddingHorizontal: 16,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 16,
  },
  headerTextWrap: {
    flex: 1,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  title: {
    fontSize: 28,
    fontWeight: '900',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 20,
  },
  exploreButton: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    minHeight: 42,
    justifyContent: 'center',
  },
  exploreButtonText: {
    fontSize: 14,
    fontWeight: '800',
  },
  infoBanner: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    marginBottom: 16,
  },
  infoBannerTitle: {
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 4,
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
    borderRadius: 16,
    padding: 14,
  },
  skeletonHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 14,
  },
  skeletonLogo: {
    width: 48,
    height: 48,
    borderRadius: 14,
  },
  skeletonHeaderText: {
    flex: 1,
    gap: 8,
  },
  skeletonScore: {
    width: 58,
    height: 44,
    borderRadius: 12,
  },
  skeletonLine: {
    height: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  stateCard: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 20,
  },
  stateTitle: {
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 8,
  },
  stateDescription: {
    fontSize: 14,
    lineHeight: 21,
  },
  stateActions: {
    marginTop: 18,
    gap: 10,
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
    fontWeight: '800',
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
    fontWeight: '800',
  },
  sectionsWrap: {
    gap: 22,
  },
  section: {
    gap: 10,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '800',
  },
  sectionDescription: {
    fontSize: 13,
    lineHeight: 19,
  },
  cardList: {
    gap: 12,
  },
});
