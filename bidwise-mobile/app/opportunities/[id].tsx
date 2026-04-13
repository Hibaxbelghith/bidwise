import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Animated,
  Image,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Redirect, useLocalSearchParams, useRouter } from 'expo-router';

import { useThemeColor } from '@/hooks/use-theme-color';
import { useAuth } from '@/src/context/AuthContext';
import {
  getOpportunityById,
  getSimilarOpportunities,
  type Opportunity,
  type SimilarOpportunity,
} from '@/src/services/opportunities';

const FALLBACK_LOGO = require('../../assets/images/icon.png');
const MIN_LOADING_TIME_MS = 450;

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
  const opacity = useMemo(() => new Animated.Value(0.55), []);

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

function formatTypeLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return TYPE_LABELS[key] || (key || 'N/A');
}

function formatStatusLabel(value?: string | null): string {
  const key = String(value || '').trim().toUpperCase();
  return STATUS_LABELS[key] || (key || 'N/A');
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

function getErrorMessage(error: unknown): string {
  const maybeError = error as {
    response?: {
      status?: number;
      data?: unknown;
    };
    message?: string;
  };

  const payload = maybeError.response?.data;
  if (typeof payload === 'object' && payload !== null) {
    const detail = (payload as Record<string, unknown>).detail;
    const message = (payload as Record<string, unknown>).error;

    if (typeof detail === 'string' && detail.trim()) return detail;
    if (typeof message === 'string' && message.trim()) return message;
  }

  if (typeof payload === 'string' && payload.includes('DisallowedHost')) {
    return 'Backend host is blocked by Django ALLOWED_HOSTS. Enable debug host allowance and retry.';
  }

  if (maybeError.response?.status === 404) {
    return 'Opportunity not found.';
  }

  return 'Unable to load this opportunity right now.';
}

function formatExperienceLabel(item: Opportunity): string {
  const experience = item.experience;
  if (!experience || typeof experience !== 'object') return 'N/A';

  const parseValue = (value: number | null | undefined): number | null => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) return null;
    return Math.floor(parsed);
  };

  const min = parseValue(experience.min);
  const max = parseValue(experience.max);

  if (min === null && max === null) return 'N/A';
  if (min !== null && max !== null) return min === max ? `${min} years` : `${min}-${max} years`;
  if (min !== null) return `${min}+ years`;
  return `Up to ${max} years`;
}

function formatList(values?: string[] | null): string {
  if (!Array.isArray(values) || values.length === 0) return 'N/A';

  const deduped: string[] = [];
  for (const rawValue of values) {
    const cleanValue = String(rawValue || '').trim();
    if (!cleanValue || deduped.includes(cleanValue)) continue;
    deduped.push(cleanValue);
  }

  if (deduped.length === 0) return 'N/A';
  return deduped.join(', ');
}

function normalizeDescription(item: Opportunity): string {
  const raw = String(item.description || '').trim();
  if (!raw) return 'No description available.';

  return raw
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
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

interface DetailRowProps {
  label: string;
  value: string;
  textColor: string;
  mutedColor: string;
}

function DetailRow({ label, value, textColor, mutedColor }: DetailRowProps) {
  return (
    <View style={styles.detailRow}>
      <Text style={[styles.detailLabel, { color: mutedColor }]}>{label}</Text>
      <Text style={[styles.detailValue, { color: textColor }]}>{value}</Text>
    </View>
  );
}

interface DetailSkeletonProps {
  cardColor: string;
  borderColor: string;
  skeletonBase: string;
  skeletonSoft: string;
}

function DetailSkeleton({ cardColor, borderColor, skeletonBase, skeletonSoft }: DetailSkeletonProps) {
  const pulse = useSkeletonPulse();

  return (
    <Animated.View style={[styles.skeletonContainer, { opacity: pulse }]}> 
      <View style={[styles.mainCard, { backgroundColor: cardColor, borderColor }]}> 
        <View style={styles.headerRow}> 
          <View style={[styles.logoWrap, { borderColor, backgroundColor: cardColor }]}> 
            <View style={[styles.skeletonBlock, { width: 44, height: 44, borderRadius: 12, backgroundColor: skeletonBase }]} />
          </View>
          <View style={styles.headerContent}> 
            <View style={[styles.skeletonBlock, { width: '82%', height: 18, marginBottom: 8, backgroundColor: skeletonBase }]} />
            <View style={[styles.skeletonBlock, { width: '58%', height: 12, backgroundColor: skeletonSoft }]} />
          </View>
        </View>

        <View style={styles.chipRow}> 
          <View style={[styles.skeletonBlock, { width: 90, height: 26, borderRadius: 999, backgroundColor: skeletonSoft }]} />
          <View style={[styles.skeletonBlock, { width: 84, height: 26, borderRadius: 999, backgroundColor: skeletonSoft }]} />
        </View>
      </View>

      <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}> 
        {[0, 1, 2, 3, 4].map((index) => (
          <View key={index} style={styles.detailRow}> 
            <View style={[styles.skeletonBlock, { width: 90, height: 12, backgroundColor: skeletonSoft }]} />
            <View style={[styles.skeletonBlock, { width: '45%', height: 14, backgroundColor: skeletonBase }]} />
          </View>
        ))}
      </View>

      <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}> 
        <View style={[styles.skeletonBlock, { width: 120, height: 16, marginBottom: 12, backgroundColor: skeletonBase }]} />
        <View style={[styles.skeletonBlock, { width: '100%', height: 12, marginBottom: 8, backgroundColor: skeletonSoft }]} />
        <View style={[styles.skeletonBlock, { width: '94%', height: 12, marginBottom: 8, backgroundColor: skeletonSoft }]} />
        <View style={[styles.skeletonBlock, { width: '82%', height: 12, backgroundColor: skeletonSoft }]} />
      </View>
    </Animated.View>
  );
}

export default function OpportunityDetailScreen() {
  const router = useRouter();
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

  const [item, setItem] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [similarItems, setSimilarItems] = useState<SimilarOpportunity[]>([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarError, setSimilarError] = useState('');

  const safeId = useMemo(() => {
    if (Array.isArray(id)) return id[0] || '';
    return String(id || '').trim();
  }, [id]);

  const hasValidOpportunityId = useMemo(() => /^\d+$/.test(safeId), [safeId]);

  useEffect(() => {
    if (!safeId || hasValidOpportunityId) return;
    router.replace('/opportunities');
  }, [hasValidOpportunityId, router, safeId]);

  const fetchDetail = useCallback(async () => {
    if (!safeId || !hasValidOpportunityId) {
      setError('Invalid opportunity id.');
      setItem(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    const startedAt = Date.now();

    try {
      const data = await getOpportunityById(safeId);
      setItem(data);
      setError('');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setItem(null);
    } finally {
      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_LOADING_TIME_MS) {
        await wait(MIN_LOADING_TIME_MS - elapsed);
      }
      setLoading(false);
    }
  }, [hasValidOpportunityId, safeId]);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      void fetchDetail();
    }
  }, [authLoading, fetchDetail, isAuthenticated]);

  useEffect(() => {
    if (!item?.id) {
      setSimilarItems([]);
      setSimilarError('');
      return;
    }

    let cancelled = false;

    const loadSimilar = async () => {
      setSimilarLoading(true);
      setSimilarError('');

      try {
        const data = await getSimilarOpportunities(item.id, 5);
        if (cancelled) return;

        const cleaned = data
          .filter((entry) => Number(entry?.id) !== Number(item.id))
          .slice(0, 5);

        setSimilarItems(cleaned);
      } catch {
        if (cancelled) return;
        setSimilarItems([]);
        setSimilarError('Unable to load similar opportunities.');
      } finally {
        if (!cancelled) {
          setSimilarLoading(false);
        }
      }
    };

    void loadSimilar();

    return () => {
      cancelled = true;
    };
  }, [item?.id]);

  const openSourceLink = useCallback(async () => {
    if (!item?.source_item_url) return;

    try {
      const supported = await Linking.canOpenURL(item.source_item_url);
      if (!supported) {
        Alert.alert('Source unavailable', 'This source URL cannot be opened on your device.');
        return;
      }
      await Linking.openURL(item.source_item_url);
    } catch {
      Alert.alert('Source unavailable', 'Failed to open this source link.');
    }
  }, [item?.source_item_url]);

  const openSimilarOpportunity = useCallback((opportunityId: number) => {
    router.push({
      pathname: '/opportunities/[id]',
      params: { id: String(opportunityId) },
    });
  }, [router]);

  const sourceLabel = String(item?.source?.nom || '').trim();
  const salaryLabel = String(item?.salary || '').trim();

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
    <ScrollView contentContainerStyle={[styles.screen, { backgroundColor }]}>
      <View style={styles.topBar}> 
        <Pressable onPress={() => router.back()}>
          <Text style={[styles.backText, { color: tintColor }]}>← Opportunities</Text>
        </Pressable>
      </View>

      {loading ? (
        <DetailSkeleton
          cardColor={cardColor}
          borderColor={borderColor}
          skeletonBase={skeletonBase}
          skeletonSoft={skeletonSoft}
        />
      ) : null}

      {!loading && error ? (
        <View style={[styles.errorCard, { backgroundColor: cardColor, borderColor }]}> 
          <Text style={[styles.errorTitle, { color: textColor }]}>Unable to load opportunity</Text>
          <Text style={[styles.errorMessage, { color: mutedColor }]}>{error}</Text>
          <Pressable style={[styles.retryButton, { backgroundColor: tintColor }]} onPress={fetchDetail}>
            <Text style={styles.retryButtonText}>Retry</Text>
          </Pressable>
        </View>
      ) : null}

      {!loading && !error && item ? (
        <>
          <View style={[styles.mainCard, { backgroundColor: cardColor, borderColor }]}> 
            <View style={styles.headerRow}> 
              <OpportunityLogo
                logoUrl={getCompanyLogoUrl(item)}
                borderColor={borderColor}
                cardColor={cardColor}
              />

              <View style={styles.headerContent}> 
                <Text style={[styles.title, { color: textColor }]}>{String(item.titre || 'Untitled opportunity')}</Text>
                <Text style={[styles.companyText, { color: mutedColor }]}>{getOrganizationLabel(item)}</Text>
              </View>
            </View>

            <View style={styles.chipRow}> 
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
            <Text style={[styles.metaText, { color: mutedColor }]}>Published: {formatDate(item.date_publication)}</Text>
            {item.date_limite ? (
              <Text style={[styles.metaText, { color: mutedColor }]}>Deadline: {formatDate(item.date_limite)}</Text>
            ) : null}

            <Pressable
              style={[
                styles.sourceButton,
                {
                  backgroundColor: item.source_item_url ? tintColor : `${tintColor}55`,
                },
              ]}
              onPress={openSourceLink}
              disabled={!item.source_item_url}
            >
              <Text style={styles.sourceButtonText}>Voir source</Text>
            </Pressable>
          </View>

          <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}> 
            <Text style={[styles.sectionTitle, { color: textColor }]}>Details</Text>

            <DetailRow
              label="Source"
              value={String(item.source?.nom || 'Unknown source')}
              textColor={textColor}
              mutedColor={mutedColor}
            />
            <DetailRow
              label="Contract"
              value={String(item.contract_type || 'N/A')}
              textColor={textColor}
              mutedColor={mutedColor}
            />
            <DetailRow
              label="Experience"
              value={formatExperienceLabel(item)}
              textColor={textColor}
              mutedColor={mutedColor}
            />
            <DetailRow
              label="Education"
              value={String(item.education_level || 'N/A')}
              textColor={textColor}
              mutedColor={mutedColor}
            />
            <DetailRow
              label="Availability"
              value={String(item.availability || 'N/A')}
              textColor={textColor}
              mutedColor={mutedColor}
            />
            <DetailRow
              label="Salary"
              value={String(item.salary || 'N/A')}
              textColor={textColor}
              mutedColor={mutedColor}
            />
            <DetailRow
              label="Languages"
              value={formatList(item.languages || item.languages_fallback || [])}
              textColor={textColor}
              mutedColor={mutedColor}
            />
            <DetailRow
              label="Skills"
              value={formatList(item.skills || [])}
              textColor={textColor}
              mutedColor={mutedColor}
            />
          </View>

          <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}> 
            <Text style={[styles.sectionTitle, { color: textColor }]}>Description</Text>
            <Text style={[styles.descriptionText, { color: mutedColor }]}>{normalizeDescription(item)}</Text>
          </View>

          <View style={[styles.sectionCard, { backgroundColor: cardColor, borderColor }]}> 
            <Text style={[styles.sectionTitle, { color: textColor }]}>Similar opportunities</Text>

            {similarLoading ? (
              <Text style={[styles.similarStateText, { color: mutedColor }]}>Finding similar opportunities...</Text>
            ) : null}

            {!similarLoading && similarError ? (
              <Text style={[styles.similarStateText, { color: mutedColor }]}>{similarError}</Text>
            ) : null}

            {!similarLoading && !similarError && similarItems.length === 0 ? (
              <Text style={[styles.similarStateText, { color: mutedColor }]}>No similar opportunities found.</Text>
            ) : null}

            {!similarLoading && !similarError && similarItems.length > 0
              ? similarItems.map((similarItem) => {
                const title = String(similarItem.titre || '').trim() || `Opportunity #${similarItem.id}`;
                const score = Number(similarItem.similarity_score);
                const hasScore = Number.isFinite(score);

                return (
                  <Pressable
                    key={similarItem.id}
                    style={[styles.similarItemRow, { borderColor }]}
                    onPress={() => openSimilarOpportunity(similarItem.id)}
                  >
                    <Text style={[styles.similarItemTitle, { color: textColor }]} numberOfLines={2}>
                      {title}
                    </Text>
                    {hasScore ? (
                      <Text style={[styles.similarItemScore, { color: mutedColor }]}>
                        {Math.round(score * 100)}% match
                      </Text>
                    ) : null}
                  </Pressable>
                );
              })
              : null}
          </View>
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flexGrow: 1,
    paddingTop: 60,
    paddingHorizontal: 18,
    paddingBottom: 30,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  topBar: {
    marginBottom: 12,
  },
  backText: {
    fontSize: 15,
    fontWeight: '600',
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
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  logoWrap: {
    width: 52,
    height: 52,
    borderRadius: 13,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  logoImage: {
    width: 50,
    height: 50,
  },
  headerContent: {
    flex: 1,
  },
  title: {
    fontSize: 18,
    lineHeight: 24,
    fontWeight: '700',
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
    fontWeight: '700',
  },
  metaText: {
    fontSize: 13,
    marginBottom: 6,
  },
  sourceButton: {
    marginTop: 8,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  sourceButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  detailLabel: {
    fontSize: 13,
    flexShrink: 0,
  },
  detailValue: {
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'right',
    flex: 1,
  },
  descriptionText: {
    fontSize: 14,
    lineHeight: 22,
  },
  similarStateText: {
    fontSize: 13,
    lineHeight: 18,
  },
  similarItemRow: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginTop: 8,
  },
  similarItemTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  similarItemScore: {
    fontSize: 12,
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
    fontWeight: '700',
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
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  skeletonBlock: {
    borderRadius: 8,
  },
});
