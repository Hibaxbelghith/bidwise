import { useMemo, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import { useDashboardData } from '../hooks/useDashboardData';
import ApplicationRow from './ApplicationRow';
import DashboardStatCard from './DashboardStatCard';
import DashboardTabs from './DashboardTabs';
import SavedOpportunityRow from './SavedOpportunityRow';

type DashboardScreenProps = {
  embedded?: boolean;
};

export default function DashboardScreen({ embedded = false }: DashboardScreenProps) {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<'saved' | 'applications'>('saved');

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const {
    savedItems,
    applications,
    loading,
    refreshing,
    error,
    notice,
    withdrawingId,
    stats,
    handleRefresh,
    handleWithdraw,
  } = useDashboardData(isAuthenticated);

  const displayName = useMemo(() => {
    const firstName = String(user?.profil?.prenom || user?.first_name || '').trim();
    return firstName || 'there';
  }, [user?.first_name, user?.profil?.prenom]);

  const emptySaved = !loading && activeTab === 'saved' && savedItems.length === 0;
  const emptyApplications = !loading && activeTab === 'applications' && applications.length === 0;

  return (
    <View style={[styles.container, { backgroundColor }]}>
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
        <View style={styles.headerBlock}>
          <Text style={[styles.greeting, { color: mutedColor }]}>
            Welcome back, {displayName}
          </Text>
          <Text style={[styles.title, { color: textColor }]}>Your space</Text>
          <Text style={[styles.subtitle, { color: mutedColor }]}>
            Track saved opportunities and follow your applications in one place.
          </Text>
        </View>

        <View style={styles.statsRow}>
          <DashboardStatCard
            value={stats.savedCount}
            label="Saved"
            cardColor={cardColor}
            borderColor={borderColor}
            textColor={textColor}
            mutedColor={mutedColor}
          />
          <DashboardStatCard
            value={stats.appliedCount}
            label="Applications"
            cardColor={cardColor}
            borderColor={borderColor}
            textColor={textColor}
            mutedColor={mutedColor}
          />
          <DashboardStatCard
            value={stats.inProgressCount}
            label="In progress"
            cardColor={cardColor}
            borderColor={borderColor}
            textColor={textColor}
            mutedColor={mutedColor}
          />
        </View>

        <DashboardTabs
          value={activeTab}
          onChange={setActiveTab}
          savedCount={stats.savedCount}
          applicationsCount={stats.appliedCount}
          cardColor={cardColor}
          borderColor={borderColor}
          textColor={textColor}
          mutedColor={mutedColor}
          tintColor={tintColor}
        />

        {error ? (
          <View style={[styles.messageCard, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.messageTitle, { color: textColor }]}>Unable to load your dashboard</Text>
            <Text style={[styles.messageText, { color: mutedColor }]}>{error}</Text>
          </View>
        ) : null}

        {!error && notice ? (
          <View style={[styles.noticeCard, { backgroundColor: `${tintColor}10`, borderColor: `${tintColor}24` }]}>
            <Text style={[styles.noticeText, { color: textColor }]}>{notice}</Text>
          </View>
        ) : null}

        {loading ? (
          <View style={[styles.messageCard, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.messageTitle, { color: textColor }]}>Loading your dashboard...</Text>
            <Text style={[styles.messageText, { color: mutedColor }]}>
              We are preparing your saved items and applications.
            </Text>
          </View>
        ) : null}

        {!loading && activeTab === 'saved' ? (
          <View style={styles.listWrap}>
            {savedItems.map((item) => (
              <SavedOpportunityRow
                key={`saved-${item.id}`}
                item={item}
                textColor={textColor}
                mutedColor={mutedColor}
                borderColor={borderColor}
                cardColor={cardColor}
                tintColor={tintColor}
                onPress={() =>
                  router.push({
                    pathname: '/opportunities/[id]',
                    params: { id: String(item.id) },
                  })
                }
              />
            ))}
          </View>
        ) : null}

        {!loading && activeTab === 'applications' ? (
          <View style={styles.listWrap}>
            {applications.map((item) => (
              <ApplicationRow
                key={`application-${item.id}`}
                item={item}
                withdrawing={withdrawingId === item.id}
                cardColor={cardColor}
                borderColor={borderColor}
                textColor={textColor}
                mutedColor={mutedColor}
                tintColor={tintColor}
                onOpen={() =>
                  router.push({
                    pathname: '/opportunities/[id]',
                    params: { id: String(item.opportunity_id) },
                  })
                }
                onWithdraw={() => handleWithdraw(item.id)}
              />
            ))}
          </View>
        ) : null}

        {emptySaved ? (
          <View style={[styles.messageCard, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.messageTitle, { color: textColor }]}>No saved opportunities yet</Text>
            <Text style={[styles.messageText, { color: mutedColor }]}>
              Save interesting roles from Explore to find them quickly here later.
            </Text>
          </View>
        ) : null}

        {emptyApplications ? (
          <View style={[styles.messageCard, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.messageTitle, { color: textColor }]}>No applications yet</Text>
            <Text style={[styles.messageText, { color: mutedColor }]}>
              Apply to a BidWise opportunity or confirm an external application to start tracking it here.
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 16,
    paddingBottom: 112,
    gap: 16,
  },
  headerBlock: {
    gap: 6,
  },
  greeting: {
    fontSize: 14,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 20,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  listWrap: {
    gap: 12,
  },
  messageCard: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 20,
    gap: 8,
  },
  messageTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  messageText: {
    fontSize: 14,
    lineHeight: 20,
  },
  noticeCard: {
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  noticeText: {
    fontSize: 13,
    lineHeight: 19,
    fontWeight: '600',
  },
});
