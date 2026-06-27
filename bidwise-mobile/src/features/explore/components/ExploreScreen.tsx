import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useState } from 'react';

import OpportunityAssistantSheet from '@/src/features/opportunities/components/OpportunityAssistantSheet';
import OpportunityCard from '@/src/features/opportunities/components/OpportunityCard';
import OpportunityCardSkeleton from '@/src/features/opportunities/components/OpportunityCardSkeleton';
import type { OpportunityTypeFilter } from '@/src/features/opportunities/hooks/useOpportunitiesList';
import type {
  Opportunity,
  OpportunitySource,
} from '@/src/features/opportunities/services/opportunitiesService';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import ExploreBanner, { type ExploreBannerMode } from './ExploreBanner';
import ExploreFiltersBar from './ExploreFiltersBar';

type ExploreScreenProps = {
  isAuthenticated: boolean;
  authLoading: boolean;
  bannerMode: ExploreBannerMode;
  bannerPrimaryLabel: string;
  onBannerAction: () => void;
  tenderOnly: boolean;
  items: Opportunity[];
  totalCount: number;
  initialLoading: boolean;
  loadingMore: boolean;
  refreshing: boolean;
  error: string;
  cityInput: string;
  setCityInput: (value: string) => void;
  typeFilter: OpportunityTypeFilter;
  setTypeFilter: (value: OpportunityTypeFilter) => void;
  sourceFilter: string;
  setSourceFilter: (value: string) => void;
  sourceOptions: OpportunitySource[];
  workModeFilter: '' | 'REMOTE' | 'HYBRID' | 'ON_SITE';
  setWorkModeFilter: (value: '' | 'REMOTE' | 'HYBRID' | 'ON_SITE') => void;
  datePostedFilter: '' | 'day' | '3days' | 'week' | '2weeks' | 'month';
  setDatePostedFilter: (value: '' | 'day' | '3days' | 'week' | '2weeks' | 'month') => void;
  hasActiveFilters: boolean;
  clearFilters: () => void;
  handleRefresh: () => void;
  handleLoadMore: () => void;
};

export default function ExploreScreen({
  isAuthenticated,
  authLoading,
  bannerMode,
  bannerPrimaryLabel,
  onBannerAction,
  tenderOnly,
  items,
  totalCount,
  initialLoading,
  loadingMore,
  refreshing,
  error,
  cityInput,
  setCityInput,
  typeFilter,
  setTypeFilter,
  sourceFilter,
  setSourceFilter,
  sourceOptions,
  workModeFilter,
  setWorkModeFilter,
  datePostedFilter,
  setDatePostedFilter,
  hasActiveFilters,
  clearFilters,
  handleRefresh,
  handleLoadMore,
}: ExploreScreenProps) {
  const router = useRouter();
  const [assistantOpportunityId, setAssistantOpportunityId] = useState<number | null>(null);

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');
  const skeletonBase = useThemeColor({ light: '#d4d4d8', dark: '#2f2f2f' }, 'border');
  const skeletonSoft = useThemeColor({ light: '#e4e4e7', dark: '#3a3a3a' }, 'card');

  const openDetail = (item: Opportunity) => {
    router.push({
      pathname: '/opportunities/[id]',
      params: { id: String(item.id) },
    });
  };

  const openLogin = () => {
    router.push('/login');
  };

  const openAssistant = (item: Opportunity) => {
    if (!isAuthenticated) {
      openLogin();
      return;
    }

    setAssistantOpportunityId(item.id);
  };

  const listHeader = (
    <View style={styles.headerContent}>
      {!tenderOnly ? (
        <ExploreBanner
          mode={bannerMode}
          primaryLabel={bannerPrimaryLabel}
          onPrimaryAction={onBannerAction}
        />
      ) : null}

      <ExploreFiltersBar
        tenderOnly={tenderOnly}
        cityInput={cityInput}
        onCityChange={setCityInput}
        typeFilter={typeFilter}
        onTypeChange={setTypeFilter}
        sourceFilter={sourceFilter}
        onSourceChange={setSourceFilter}
        sourceOptions={sourceOptions}
        workModeFilter={workModeFilter}
        onWorkModeChange={setWorkModeFilter}
        datePostedFilter={datePostedFilter}
        onDatePostedChange={setDatePostedFilter}
        hasActiveFilters={hasActiveFilters}
        onClearFilters={clearFilters}
        totalCount={totalCount}
        cardColor={cardColor}
        borderColor={borderColor}
        textColor={textColor}
        mutedColor={mutedColor}
        tintColor={tintColor}
      />

      {error && items.length > 0 ? (
        <View style={[styles.inlineError, { backgroundColor: cardColor, borderColor }]}>
          <Text style={[styles.inlineErrorText, { color: mutedColor }]}>{error}</Text>
        </View>
      ) : null}
    </View>
  );

  if (authLoading) {
    return (
      <View style={[styles.centered, { backgroundColor }]}>
        <ActivityIndicator size="large" color={tintColor} />
      </View>
    );
  }

  if (initialLoading && items.length === 0) {
    return (
      <View style={[styles.screen, { backgroundColor }]}>
        {listHeader}
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
      </View>
    );
  }

  if (!initialLoading && items.length === 0 && error) {
    return (
      <View style={[styles.screen, { backgroundColor }]}>
        {listHeader}
        <View style={[styles.emptyState, { backgroundColor: cardColor, borderColor }]}>
          <Text style={[styles.emptyTitle, { color: textColor }]}>Unable to load opportunities</Text>
          <Text style={[styles.emptySubtitle, { color: mutedColor }]}>{error}</Text>
          <TouchableOpacity
            activeOpacity={0.85}
            onPress={handleRefresh}
            style={[styles.retryButton, { backgroundColor: tintColor }]}
          >
            <Text style={styles.retryButtonText}>Try again</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <>
      <FlatList
        style={[styles.screen, { backgroundColor }]}
        contentContainerStyle={styles.listContent}
        data={items}
        keyExtractor={(item) => String(item.id)}
        ListHeaderComponent={listHeader}
        renderItem={({ item }) => (
          <OpportunityCard
            item={item}
            cardColor={cardColor}
            borderColor={borderColor}
            textColor={textColor}
            mutedColor={mutedColor}
            tintColor={tintColor}
            isUserAuthenticated={isAuthenticated}
            onPress={() => openDetail(item)}
            onRequireLogin={openLogin}
            onOpenAssistant={() => openAssistant(item)}
          />
        )}
        refreshControl={(
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={tintColor}
            colors={[tintColor]}
          />
        )}
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.3}
        keyboardShouldPersistTaps="handled"
        initialNumToRender={6}
        maxToRenderPerBatch={8}
        removeClippedSubviews
        windowSize={7}
        ListEmptyComponent={
          !initialLoading && !error ? (
            <View style={[styles.emptyState, { backgroundColor: cardColor, borderColor }]}>
              <Text style={[styles.emptyTitle, { color: textColor }]}>No opportunities found</Text>
              <Text style={[styles.emptySubtitle, { color: mutedColor }]}>
                Adjust filters or search terms to widen your results.
              </Text>
            </View>
          ) : null
        }
        ListFooterComponent={
          loadingMore ? (
            <View style={styles.footerLoader}>
              <ActivityIndicator color={tintColor} />
            </View>
          ) : null
        }
      />

      <OpportunityAssistantSheet
        opportunityId={assistantOpportunityId}
        visible={Boolean(assistantOpportunityId)}
        onClose={() => setAssistantOpportunityId(null)}
        colors={{
          background: backgroundColor,
          card: cardColor,
          border: borderColor,
          text: textColor,
          muted: mutedColor,
          tint: tintColor,
        }}
      />
    </>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerContent: {
    gap: 14,
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
  },
  inlineError: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  inlineErrorText: {
    fontSize: 13,
    lineHeight: 18,
  },
  listContent: {
    paddingBottom: 112,
    gap: 12,
  },
  skeletonList: {
    gap: 12,
    paddingHorizontal: 16,
  },
  emptyState: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 22,
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 6,
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
  },
  footerLoader: {
    paddingVertical: 18,
  },
  retryButton: {
    marginTop: 16,
    minHeight: 44,
    borderRadius: 12,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
});
