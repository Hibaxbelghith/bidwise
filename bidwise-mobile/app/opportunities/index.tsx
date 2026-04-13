import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  FlatList,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Redirect, useRouter } from 'expo-router';

import { useThemeColor } from '@/hooks/use-theme-color';
import { useAuth } from '@/src/context/AuthContext';
import { getOpportunities, type Opportunity } from '@/src/services/opportunities';

const FALLBACK_LOGO = require('../../assets/images/icon.png');

const MIN_LOADING_TIME_MS = 450;
const PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 350;

type FetchMode = 'initial' | 'refresh' | 'more';

type TypeOption = {
  value: 'ALL' | 'EMPLOI' | 'STAGE' | 'SAISONNIER' | 'RECHERCHE' | 'PROJET' | 'FINANCEMENT';
  label: string;
};

const TYPE_FILTER_OPTIONS: TypeOption[] = [
  { value: 'ALL', label: 'All' },
  { value: 'EMPLOI', label: 'Job' },
  { value: 'STAGE', label: 'Internship' },
  { value: 'SAISONNIER', label: 'Seasonal' },
  { value: 'RECHERCHE', label: 'Research' },
  { value: 'PROJET', label: 'Project' },
  { value: 'FINANCEMENT', label: 'Funding' },
];

const TYPE_LABELS: Record<string, string> = {
  EMPLOI: 'Job',
  STAGE: 'Internship',
  SAISONNIER: 'Seasonal',
  RECHERCHE: 'Research',
  PROJET: 'Project',
  FINANCEMENT: 'Funding',
};

const STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Active',
  EXPIREE: 'Expired',
  ARCHIVEE: 'Archived',
};

const ANONYMOUS_ORGANIZATION_PATTERN = /entreprise\s+anonyme/i;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function useSkeletonPulse() {
  const opacity = useRef(new Animated.Value(0.55)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 650,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.55,
          duration: 650,
          useNativeDriver: true,
        }),
      ]),
    );

    loop.start();

    return () => {
      loop.stop();
    };
  }, [opacity]);

  return opacity;
}

function formatDate(value?: string | null): string {
  if (!value) return 'N/A';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return date.toLocaleDateString();
}

function getOpportunityTitle(item: Opportunity): string {
  const title = String(item.titre || '').trim();
  return title || 'Untitled opportunity';
}

function getOrganizationLabel(item: Opportunity): string {
  const organization = String(item.organisation_nom || '').trim();
  if (!organization || ANONYMOUS_ORGANIZATION_PATTERN.test(organization)) {
    return 'Entreprise confidentielle';
  }
  return organization;
}

function getCompanyLogoUrl(item: Opportunity): string {
  return String(item.company_logo || '').trim();
}

function getDescriptionPreview(item: Opportunity): string {
  const rawDescription = String(item.description || '').trim();
  if (!rawDescription) return 'No description available.';

  const cleaned = rawDescription.replace(/\s+/g, ' ').trim();
  return cleaned.length > 170 ? `${cleaned.slice(0, 170)}...` : cleaned;
}

function formatTypeLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return TYPE_LABELS[key] || (key || 'N/A');
}

function formatStatusLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return STATUS_LABELS[key] || (key || 'N/A');
}

function getErrorMessage(error: unknown): string {
  const maybeError = error as {
    response?: {
      status?: number;
      data?: unknown;
    };
  };

  const payload = maybeError.response?.data;
  if (typeof payload === 'object' && payload !== null) {
    const detail = (payload as Record<string, unknown>).detail;
    const msg = (payload as Record<string, unknown>).error;

    if (typeof detail === 'string' && detail.trim()) return detail;
    if (typeof msg === 'string' && msg.trim()) return msg;
  }

  if (typeof payload === 'string' && payload.includes('DisallowedHost')) {
    return 'Backend host is blocked by Django ALLOWED_HOSTS. Enable debug host allowance and retry.';
  }

  if (maybeError.response?.status === 401) {
    return 'Session expired. Please login again.';
  }

  return 'Unable to load opportunities right now.';
}

interface OpportunityLogoProps {
  logoUrl: string;
  borderColor: string;
  cardColor: string;
}

function OpportunityLogo({ logoUrl, borderColor, cardColor }: OpportunityLogoProps) {
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    setImageError(false);
  }, [logoUrl]);

  const useRemoteImage = Boolean(logoUrl) && !imageError;

  return (
    <View style={[styles.logoWrap, { borderColor, backgroundColor: cardColor }]}> 
      <Image
        source={useRemoteImage ? { uri: logoUrl } : FALLBACK_LOGO}
        style={styles.logoImage}
        resizeMode="cover"
        onError={() => setImageError(true)}
      />
    </View>
  );
}

interface OpportunityCardProps {
  item: Opportunity;
  cardColor: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
  onPress: () => void;
}

function OpportunityCard({
  item,
  cardColor,
  borderColor,
  textColor,
  mutedColor,
  tintColor,
  onPress,
}: OpportunityCardProps) {
  const salaryLabel = String(item.salary || '').trim();
  const sourceLabel = String(item.source?.nom || '').trim();

  return (
    <Pressable
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: cardColor,
          borderColor,
          opacity: pressed ? 0.92 : 1,
        },
      ]}
      onPress={onPress}
    >
      <View style={styles.cardHeader}>
        <OpportunityLogo
          logoUrl={getCompanyLogoUrl(item)}
          borderColor={borderColor}
          cardColor={cardColor}
        />

        <View style={styles.cardHeaderTextWrap}>
          <Text numberOfLines={2} style={[styles.cardTitle, { color: textColor }]}>
            {getOpportunityTitle(item)}
          </Text>
          <Text numberOfLines={1} style={[styles.cardSubtitle, { color: mutedColor }]}> 
            {getOrganizationLabel(item)}
          </Text>
        </View>
      </View>

      <View style={styles.chipsRow}>
        <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}18` }]}>
          <Text style={[styles.chipText, { color: tintColor }]}>{formatTypeLabel(item.type_opportunite)}</Text>
        </View>
        {sourceLabel ? (
          <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}10` }]}>
            <Text style={[styles.chipText, { color: textColor }]}>{sourceLabel}</Text>
          </View>
        ) : null}
        {salaryLabel ? (
          <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}10` }]}>
            <Text style={[styles.chipText, { color: textColor }]}>{salaryLabel}</Text>
          </View>
        ) : null}
        <View style={[styles.chip, { borderColor, backgroundColor: `${tintColor}10` }]}>
          <Text style={[styles.chipText, { color: textColor }]}>{formatStatusLabel(item.statut)}</Text>
        </View>
      </View>

      <Text style={[styles.metaText, { color: mutedColor }]}> 
        {String(item.ville || '').trim() || 'Location unavailable'}
      </Text>
      <Text style={[styles.metaText, { color: mutedColor }]}> 
        Published: {formatDate(item.date_publication)}
      </Text>

      <Text numberOfLines={3} style={[styles.descriptionText, { color: mutedColor }]}>
        {getDescriptionPreview(item)}
      </Text>
    </Pressable>
  );
}

interface OpportunitySkeletonProps {
  cardColor: string;
  borderColor: string;
  skeletonBase: string;
  skeletonSoft: string;
}

function OpportunityCardSkeleton({ cardColor, borderColor, skeletonBase, skeletonSoft }: OpportunitySkeletonProps) {
  const pulse = useSkeletonPulse();

  return (
    <Animated.View style={{ opacity: pulse }}>
      <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}> 
        <View style={styles.cardHeader}>
          <View style={[styles.logoWrap, { borderColor, backgroundColor: cardColor }]}> 
            <View style={[styles.skeletonBlock, { width: 40, height: 40, borderRadius: 12, backgroundColor: skeletonBase }]} />
          </View>

          <View style={[styles.cardHeaderTextWrap, { gap: 8 }]}> 
            <View style={[styles.skeletonBlock, { width: '90%', height: 16, backgroundColor: skeletonBase }]} />
            <View style={[styles.skeletonBlock, { width: '60%', height: 12, backgroundColor: skeletonSoft }]} />
          </View>
        </View>

        <View style={styles.chipsRow}>
          <View style={[styles.skeletonBlock, { width: 90, height: 26, borderRadius: 999, backgroundColor: skeletonSoft }]} />
          <View style={[styles.skeletonBlock, { width: 80, height: 26, borderRadius: 999, backgroundColor: skeletonSoft }]} />
          <View style={[styles.skeletonBlock, { width: 100, height: 26, borderRadius: 999, backgroundColor: skeletonSoft }]} />
        </View>

        <View style={[styles.skeletonBlock, { width: '45%', height: 12, marginBottom: 8, backgroundColor: skeletonSoft }]} />
        <View style={[styles.skeletonBlock, { width: '55%', height: 12, marginBottom: 12, backgroundColor: skeletonSoft }]} />
        <View style={[styles.skeletonBlock, { width: '100%', height: 12, marginBottom: 6, backgroundColor: skeletonSoft }]} />
        <View style={[styles.skeletonBlock, { width: '88%', height: 12, backgroundColor: skeletonSoft }]} />
      </View>
    </Animated.View>
  );
}

export default function OpportunitiesListScreen() {
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

  const [searchInput, setSearchInput] = useState('');
  const [cityInput, setCityInput] = useState('');
  const [minSalaryInput, setMinSalaryInput] = useState('');
  const [typeFilter, setTypeFilter] = useState<TypeOption['value']>('ALL');

  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [debouncedCity, setDebouncedCity] = useState('');
  const [debouncedMinSalary, setDebouncedMinSalary] = useState('');

  const [items, setItems] = useState<Opportunity[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);

  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const fetchLockRef = useRef(false);
  const hasLoadedRef = useRef(false);
  const hasNextRef = useRef(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setDebouncedCity(cityInput.trim());
      setDebouncedMinSalary(minSalaryInput.trim());
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
    };
  }, [cityInput, minSalaryInput, searchInput]);

  const minSalaryFilter = useMemo(() => {
    const digits = debouncedMinSalary.replace(/[^0-9]/g, '');
    if (!digits) return undefined;

    const parsed = Number.parseInt(digits, 10);
    if (!Number.isFinite(parsed) || parsed <= 0) return undefined;
    return parsed;
  }, [debouncedMinSalary]);

  const hasActiveFilters = useMemo(() => {
    return Boolean(
      searchInput.trim() || cityInput.trim() || minSalaryInput.trim() || typeFilter !== 'ALL',
    );
  }, [cityInput, minSalaryInput, searchInput, typeFilter]);

  const fetchPage = useCallback(async (targetPage: number, mode: FetchMode) => {
    if (fetchLockRef.current) return;
    if (mode === 'more' && !hasNextRef.current) return;

    fetchLockRef.current = true;

    if (mode === 'initial') setInitialLoading(true);
    if (mode === 'refresh') setRefreshing(true);
    if (mode === 'more') setLoadingMore(true);

    const startedAt = Date.now();

    try {
      const data = await getOpportunities({
        page: targetPage,
        pageSize: PAGE_SIZE,
        search: debouncedSearch,
        city: debouncedCity,
        type: typeFilter === 'ALL' ? '' : typeFilter,
        minSalary: minSalaryFilter,
      });

      setItems((prev) => {
        if (targetPage === 1) return data.results;

        const knownIds = new Set(prev.map((entry) => entry.id));
        const nextItems = data.results.filter((entry) => !knownIds.has(entry.id));
        return [...prev, ...nextItems];
      });

      const nextAvailable = Boolean(data.next);
      setTotalCount(data.count);
      setPage(targetPage);
      setHasNext(nextAvailable);
      hasNextRef.current = nextAvailable;
      setError('');
      hasLoadedRef.current = true;
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      if (targetPage === 1) {
        setItems([]);
        setHasNext(false);
        hasNextRef.current = false;
      }
    } finally {
      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_LOADING_TIME_MS) {
        await wait(MIN_LOADING_TIME_MS - elapsed);
      }

      if (mode === 'initial') setInitialLoading(false);
      if (mode === 'refresh') setRefreshing(false);
      if (mode === 'more') setLoadingMore(false);

      fetchLockRef.current = false;
    }
  }, [debouncedCity, debouncedSearch, minSalaryFilter, typeFilter]);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      const mode: FetchMode = hasLoadedRef.current ? 'refresh' : 'initial';
      void fetchPage(1, mode);
    }
  }, [authLoading, isAuthenticated, fetchPage]);

  const handleRefresh = useCallback(() => {
    void fetchPage(1, 'refresh');
  }, [fetchPage]);

  const handleLoadMore = useCallback(() => {
    if (initialLoading || refreshing || loadingMore || !hasNext) return;
    void fetchPage(page + 1, 'more');
  }, [fetchPage, hasNext, initialLoading, loadingMore, page, refreshing]);

  const handleOpenDetail = useCallback((item: Opportunity) => {
    router.push({
      pathname: '/opportunities/[id]',
      params: { id: String(item.id) },
    });
  }, [router]);

  const handleBackToDashboard = useCallback(() => {
    router.replace('/dashboard');
  }, [router]);

  const clearFilters = useCallback(() => {
    setSearchInput('');
    setCityInput('');
    setMinSalaryInput('');
    setTypeFilter('ALL');
  }, []);

  if (!authLoading && !isAuthenticated) {
    return <Redirect href="/login" />;
  }

  if (authLoading) {
    return (
      <View style={[styles.screen, styles.centered, { backgroundColor }]}> 
        <ActivityIndicator size="large" color={tintColor} />
      </View>
    );
  }

  return (
    <View style={[styles.screen, { backgroundColor }]}> 
      <View style={styles.header}> 
        <Pressable onPress={handleBackToDashboard}>
          <Text style={[styles.backText, { color: tintColor }]}>← Dashboard</Text>
        </Pressable>
        <Text style={[styles.headerTitle, { color: textColor }]}>Opportunities</Text>
        <Text style={[styles.countText, { color: mutedColor }]}>{totalCount}</Text>
      </View>

      <View style={[styles.filtersCard, { backgroundColor: cardColor, borderColor }]}> 
        <TextInput
          value={searchInput}
          onChangeText={setSearchInput}
          placeholder="Search title, description..."
          placeholderTextColor={mutedColor}
          style={[styles.filterInput, { color: textColor, borderColor, backgroundColor }]}
        />

        <View style={styles.filterRow}> 
          <TextInput
            value={cityInput}
            onChangeText={setCityInput}
            placeholder="City"
            placeholderTextColor={mutedColor}
            style={[styles.filterInput, styles.filterHalfInput, { color: textColor, borderColor, backgroundColor }]}
          />
          <TextInput
            value={minSalaryInput}
            onChangeText={setMinSalaryInput}
            placeholder="Min salary"
            placeholderTextColor={mutedColor}
            keyboardType="numeric"
            style={[styles.filterInput, styles.filterHalfInput, { color: textColor, borderColor, backgroundColor }]}
          />
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.typeFiltersRow}>
          {TYPE_FILTER_OPTIONS.map((option) => {
            const selected = typeFilter === option.value;
            return (
              <Pressable
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
          <Pressable onPress={clearFilters} style={styles.clearFiltersButton}>
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
          {[0, 1, 2, 3].map((index) => (
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
          <Text style={[styles.emptyTitle, { color: textColor }]}>Unable to load opportunities</Text>
          <Text style={[styles.emptySubtitle, { color: mutedColor }]}>{error}</Text>
          <Pressable style={[styles.retryButton, { backgroundColor: tintColor }]} onPress={handleRefresh}>
            <Text style={styles.retryButtonText}>Try again</Text>
          </Pressable>
        </View>
      ) : null}

      {!initialLoading && items.length === 0 && !error ? (
        <View style={[styles.emptyState, { backgroundColor: cardColor, borderColor }]}> 
          <Text style={[styles.emptyTitle, { color: textColor }]}>No opportunities found</Text>
          <Text style={[styles.emptySubtitle, { color: mutedColor }]}>Adjust filters or pull to refresh.</Text>
        </View>
      ) : null}

      {items.length > 0 ? (
        <FlatList
          data={items}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.listContent}
          renderItem={({ item }) => (
            <OpportunityCard
              item={item}
              cardColor={cardColor}
              borderColor={borderColor}
              textColor={textColor}
              mutedColor={mutedColor}
              tintColor={tintColor}
              onPress={() => handleOpenDetail(item)}
            />
          )}
          refreshControl={
            <RefreshControl
              tintColor={tintColor}
              colors={[tintColor]}
              refreshing={refreshing}
              onRefresh={handleRefresh}
            />
          }
          onEndReachedThreshold={0.3}
          onEndReached={handleLoadMore}
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
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    paddingTop: 60,
    paddingHorizontal: 18,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  backText: {
    fontSize: 15,
    fontWeight: '600',
    minWidth: 88,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '700',
  },
  countText: {
    minWidth: 40,
    textAlign: 'right',
    fontSize: 14,
    fontWeight: '600',
  },
  filtersCard: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    marginBottom: 10,
  },
  filterRow: {
    flexDirection: 'row',
    gap: 8,
  },
  filterInput: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    marginBottom: 8,
  },
  filterHalfInput: {
    flex: 1,
  },
  typeFiltersRow: {
    gap: 8,
    paddingBottom: 4,
  },
  typeFilterButton: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  typeFilterText: {
    fontSize: 12,
    fontWeight: '700',
  },
  clearFiltersButton: {
    alignSelf: 'flex-end',
    marginTop: 6,
  },
  clearFiltersText: {
    fontSize: 13,
    fontWeight: '700',
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
    paddingBottom: 24,
    gap: 12,
  },
  skeletonList: {
    gap: 12,
  },
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  logoWrap: {
    width: 48,
    height: 48,
    borderRadius: 13,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  logoImage: {
    width: 46,
    height: 46,
  },
  cardHeaderTextWrap: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 3,
  },
  cardSubtitle: {
    fontSize: 13,
  },
  chipsRow: {
    flexDirection: 'row',
    alignItems: 'center',
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
    fontWeight: '600',
  },
  metaText: {
    fontSize: 12,
    marginBottom: 5,
  },
  descriptionText: {
    fontSize: 13,
    lineHeight: 18,
    marginTop: 6,
  },
  skeletonBlock: {
    borderRadius: 8,
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
    fontWeight: '700',
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
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
});
