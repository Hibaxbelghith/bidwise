import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { formatDateTime } from '@/src/features/opportunities/utils/opportunityFormatters';

import type { CandidateApplication } from '../services/dashboardService';
import {
  canWithdrawApplication,
  getMobileApplicationStatusMeta,
} from '../utils/applicationStatus';

type ApplicationRowProps = {
  item: CandidateApplication;
  withdrawing: boolean;
  cardColor: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
  onOpen: () => void;
  onWithdraw: () => Promise<void>;
};

const TONE_STYLES = {
  blue: { bg: 'rgba(37, 99, 235, 0.10)', text: '#2563eb' },
  green: { bg: 'rgba(22, 163, 74, 0.10)', text: '#15803d' },
  red: { bg: 'rgba(220, 38, 38, 0.10)', text: '#dc2626' },
  amber: { bg: 'rgba(217, 119, 6, 0.12)', text: '#b45309' },
  neutral: { bg: 'rgba(148, 163, 184, 0.14)', text: '#475569' },
} as const;

export default function ApplicationRow({
  item,
  withdrawing,
  cardColor,
  borderColor,
  textColor,
  mutedColor,
  tintColor,
  onOpen,
  onWithdraw,
}: ApplicationRowProps) {
  const statusMeta = getMobileApplicationStatusMeta(item.statut);
  const tone = TONE_STYLES[statusMeta.tone];
  const canWithdraw = canWithdrawApplication(item.statut);

  const handleWithdrawPress = () => {
    Alert.alert(
      'Withdraw application?',
      `You will no longer be considered for "${item.opportunity_title}".`,
      [
        { text: 'Keep', style: 'cancel' },
        {
          text: withdrawing ? 'Withdrawing...' : 'Withdraw',
          style: 'destructive',
          onPress: () => {
            void onWithdraw();
          },
        },
      ],
    );
  };

  return (
    <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <Text numberOfLines={2} style={[styles.title, { color: textColor }]}>
            {item.opportunity_title}
          </Text>
          {!!item.organisation_name && (
            <Text numberOfLines={1} style={[styles.meta, { color: mutedColor }]}>
              {item.organisation_name}
            </Text>
          )}
          <Text numberOfLines={1} style={[styles.meta, { color: mutedColor }]}>
            {[item.ville, `${statusMeta.datePrefix} ${formatDateTime(item.submitted_at)}`]
              .filter(Boolean)
              .join(' • ')}
          </Text>
        </View>

        <View style={[styles.statusBadge, { backgroundColor: tone.bg }]}>
          <Text style={[styles.statusText, { color: tone.text }]}>{statusMeta.label}</Text>
        </View>
      </View>

      <View style={styles.actions}>
        <Pressable
          accessibilityRole="button"
          onPress={onOpen}
          style={[styles.secondaryButton, { borderColor }]}
        >
          <Text style={[styles.secondaryButtonText, { color: textColor }]}>View</Text>
        </Pressable>

        {canWithdraw ? (
          <Pressable
            accessibilityRole="button"
            onPress={handleWithdrawPress}
            style={[styles.primaryButton, { backgroundColor: tintColor }]}
          >
            <Text style={styles.primaryButtonText}>{withdrawing ? 'Withdrawing...' : 'Withdraw'}</Text>
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    gap: 14,
  },
  header: {
    gap: 12,
  },
  headerContent: {
    gap: 6,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    lineHeight: 22,
  },
  meta: {
    fontSize: 13,
    lineHeight: 18,
  },
  statusBadge: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '700',
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
  },
  secondaryButton: {
    flex: 1,
    minHeight: 44,
    borderWidth: 1,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
  },
  secondaryButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  primaryButton: {
    flex: 1,
    minHeight: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
});
