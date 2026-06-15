import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import useOpportunitiesList, { type OpportunityTypeFilter } from '../hooks/useOpportunitiesList';
import type { Opportunity } from '../services/opportunitiesService';
import OpportunityCard from './OpportunityCard';
import OpportunityCardSkeleton from './OpportunityCardSkeleton';

const TYPE_FILTER_OPTIONS: Array<{ value: OpportunityTypeFilter; label: string }> = [
  { value: 'ALL', label: 'All' },
  { value: 'EMPLOI', label: 'Job' },
  { value: 'STAGE', label: 'Intern' },
  { value: 'SAISONNIER', label: 'Seasonal' },
  { value: 'RECHERCHE', label: 'Research' },
  { value: 'PROJET', label: 'Project' },
  { value: 'FINANCEMENT', label: 'Funding' },
];

type OpportunitiesListScreenProps = {
  embedded?: boolean;
};

export default function OpportunitiesListScreen({ embedded = false }: OpportunitiesListScreenProps) {
  const router = useRouter();
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
    cityInput,
    clearFilters,
    error,
    handleLoadMore,
    handleRefresh,
    hasActiveFilters,
    initialLoading,
    items,
    loadingMore,
    refreshing,
    searchInput,
    setCityInput,
    setSearchInput,
    setTypeFilter,
    totalCount,
    typeFilter,
  } = useOpportunitiesList({ ready: !authLoading });

  const handleBack = () => {
    if (isUserAuthenticated) {
      router.replace('/explore');
      return;
    }

    router.replace('/login');
  };

  const handleOpenDetail = (item: Opportunity) => {
    router.push({
      pathname: '/opportunities/[id]',
      params: { id: String(item.id) },
    });
  };

  if (authLoading) {
    return (
      <View style={[styles.screen, styles.centered, { backgroundColor }]}>
        <ActivityIndicator size="large" color={tintColor} />
      </View>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor }]}>
      <View style={[styles.screen, { backgroundColor, paddingTop: embedded ? 16 : 56 }]}>
        {!embedded ? (
          <View style={styles.header}>
            <Pressable
              accessibilityLabel="Go back"
              accessibilityRole="button"
              onPress={handleBack}
            >
              <Text style={[styles.backText, { color: tintColor }]}>Back</Text>
            </Pressable>
            <Text style={[styles.headerTitle, { color: textColor }]}>Opportunities</Text>
            <Text style={[styles.countText, { color: mutedColor }]}>{totalCount}</Text>
          </View>
        ) : null}

        {!isUserAuthenticated ? (
          <View style={[styles.guestBanner, { backgroundColor: cardColor, borderColor }]}>
            <View style={styles.guestBannerTextWrap}>
              <Text style={[styles.guestBannerTitle, { color: textColor }]}>Guest mode</Text>
              <Text style={[styles.guestBannerText, { color: mutedColor }]}>
                Core data open. AI features locked.
              </Text>
              <Text style={[styles.guestBannerSubText, { color: mutedColor }]}>
                Login in one tap for full BidWise value.
              </Text>
            </View>
            <Pressable
              accessibilityLabel="Login quickly"
              accessibilityRole="button"
              onPress={() => router.push('/login')}
              style={[styles.guestBannerButton, { backgroundColor: tintColor }]}
            >
              <Text style={styles.guestBannerButtonText}>Quick login</Text>
            </Pressable>
          </View>
        ) : null}

        <View style={[styles.filtersCard, { backgroundColor: cardColor, borderColor }]}>
          <TextInput
            value={searchInput}
            onChangeText={setSearchInput}
            placeholder="Search title or keyword"
            placeholderTextColor={mutedColor}
            style={[styles.filterInput, { color: textColor, borderColor, backgroundColor }]}
          />

          <TextInput
            value={cityInput}
            onChangeText={setCityInput}
            placeholder="City"
            placeholderTextColor={mutedColor}
            style={[styles.filterInput, { color: textColor, borderColor, backgroundColor }]}
          />

          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.typeFiltersRow}
          >
            {TYPE_FILTER_OPTIONS.map((option) => {
              const selected = typeFilter === option.value;

              return (
                <Pressable
                  accessibilityLabel={`Filter by type ${option.label}`}
                  accessibilityRole="button"
                  key={option.value}
                  onPress={() => setTypeFilter(option.value)}
                  style={[
                    styles.typeFilterButton,
                    {
                      borderColor: selected ? tintColor : borderColor,
                      backgroundColor: selected ? `${tintColor}20` : cardColor,
                    },
                  ]}
                >
                  <Text style={[styles.typeFilterText, { color: selected ? tintColor : textColor }]}>
                    {option.label}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>

          {hasActiveFilters ? (
            <Pressable
              accessibilityRole="button"
              onPress={clearFilters}
              style={styles.clearFiltersButton}
            >
              <Text style={[styles.clearFiltersText, { color: tintColor }]}>Reset filters</Text>
            </Pressable>
          ) : null}
        </View>

        {error && items.length > 0 ? (
          <View style={[styles.inlineError, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.inlineErrorText, { color: mutedColor }]}>{error}</Text>
          </View>
        ) : null}

        {initialLoading && items.length === 0 ? (
          <View style={styles.skeletonList}>
            {[0, 1, 2].map((index) => (
              <OpportunityCardSkeleton
                key={index}
                cardColor={cardColor}
                borderColor={borderColor}
                skeletonBase={skeletonBase}
                skeletonSoft={skeletonSoft}
              />
            ))}
          </View>
        ) : null}

        {!initialLoading && items.length === 0 && error ? (
          <View style={[styles.emptyState, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.emptyTitle, { color: textColor }]}>
              Unable to load opportunities
            </Text>
            <Text style={[styles.emptySubtitle, { color: mutedColor }]}>{error}</Text>
            <Pressable
              style={[styles.retryButton, { backgroundColor: tintColor }]}
              onPress={handleRefresh}
            >
              <Text style={styles.retryButtonText}>Try again</Text>
            </Pressable>
          </View>
        ) : null}

        {!initialLoading && items.length === 0 && !error ? (
          <View style={[styles.emptyState, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.emptyTitle, { color: textColor }]}>No opportunities found</Text>
            <Text style={[styles.emptySubtitle, { color: mutedColor }]}>
              Adjust filters or pull to refresh.
            </Text>
          </View>
        ) : null}

        {items.length > 0 ? (
          <FlatList
            data={items}
            keyExtractor={(item) => String(item.id)}
            contentContainerStyle={styles.listContent}
            initialNumToRender={6}
            keyboardShouldPersistTaps="handled"
            maxToRenderPerBatch={8}
            removeClippedSubviews
            renderItem={({ item }) => (
              <OpportunityCard
                item={item}
                cardColor={cardColor}
                borderColor={borderColor}
                textColor={textColor}
                mutedColor={mutedColor}
                tintColor={tintColor}
                isUserAuthenticated={isUserAuthenticated}
                onPress={() => handleOpenDetail(item)}
              />
            )}
            refreshControl={
              <RefreshControl
                colors={[tintColor]}
                refreshing={refreshing}
                tintColor={tintColor}
                onRefresh={handleRefresh}
              />
            }
            windowSize={7}
            onEndReached={handleLoadMore}
            onEndReachedThreshold={0.3}
            ListFooterComponent={
              loadingMore ? (
                <View style={styles.footerLoader}>
                  <ActivityIndicator color={tintColor} />
                </View>
              ) : null
            }
          />
        ) : null}
      </View>

    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  screen: {
    flex: 1,
    paddingHorizontal: 16,
    paddingBottom: 10,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  backText: {
    fontSize: 15,
    fontWeight: '700',
    minWidth: 60,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '800',
  },
  countText: {
    minWidth: 42,
    textAlign: 'right',
    fontSize: 14,
    fontWeight: '700',
  },
  guestBanner: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  guestBannerTextWrap: {
    flex: 1,
  },
  guestBannerTitle: {
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 2,
  },
  guestBannerText: {
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 2,
  },
  guestBannerSubText: {
    fontSize: 11,
    lineHeight: 16,
    fontWeight: '600',
  },
  guestBannerButton: {
    minHeight: 44,
    borderRadius: 10,
    paddingHorizontal: 14,
    justifyContent: 'center',
  },
  guestBannerButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
  filtersCard: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 10,
    marginBottom: 10,
  },
  filterInput: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    marginBottom: 8,
  },
  typeFiltersRow: {
    gap: 8,
    paddingBottom: 4,
  },
  typeFilterButton: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 11,
    paddingVertical: 7,
  },
  typeFilterText: {
    fontSize: 12,
    fontWeight: '700',
  },
  clearFiltersButton: {
    alignSelf: 'flex-end',
    marginTop: 4,
  },
  clearFiltersText: {
    fontSize: 13,
    fontWeight: '800',
  },
  inlineError: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 10,
  },
  inlineErrorText: {
    fontSize: 13,
    lineHeight: 18,
  },
  listContent: {
    paddingBottom: 96,
    gap: 12,
  },
  skeletonList: {
    gap: 12,
  },
  footerLoader: {
    paddingVertical: 16,
  },
  emptyState: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 22,
    alignItems: 'center',
    marginTop: 18,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '800',
    textAlign: 'center',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 16,
  },
  retryButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 10,
    minHeight: 42,
    justifyContent: 'center',
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
});
