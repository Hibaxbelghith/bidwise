import { useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import {
  getProfileUpdateErrorMessage,
  updateProfile,
} from '@/src/features/profile/services/profileService';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

export default function SettingsScreen() {
  const { user, loadUserProfile, loading } = useAuth();

  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');
  const backgroundColor = useThemeColor({}, 'background');

  const [isVisible, setIsVisible] = useState(user?.profil?.profile_visibility !== false);
  const [savingVisibility, setSavingVisibility] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    setIsVisible(user?.profil?.profile_visibility !== false);
  }, [user?.profil?.profile_visibility]);

  const handleVisibilityChange = async (nextValue: boolean) => {
    const previousValue = isVisible;
    setIsVisible(nextValue);
    setSavingVisibility(true);
    setError('');
    setSuccessMessage('');

    try {
      await updateProfile({ profile_visibility: nextValue });
      await loadUserProfile();
      setSuccessMessage(
        nextValue
          ? 'Your profile is now visible to recruiters.'
          : 'Your profile is now hidden from recruiters.',
      );
    } catch (updateError) {
      setIsVisible(previousValue);
      setError(
        getProfileUpdateErrorMessage(
          updateError,
          'Could not update profile visibility right now.',
        ),
      );
    } finally {
      setSavingVisibility(false);
    }
  };

  return (
    <ScrollView
      style={[styles.content, { backgroundColor }]}
      contentContainerStyle={styles.contentContainer}
      refreshControl={
        <RefreshControl
          refreshing={loading}
          onRefresh={loadUserProfile}
          tintColor={tintColor}
          colors={[tintColor]}
        />
      }
      showsVerticalScrollIndicator={false}
    >
      <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
        <Text style={[styles.cardTitle, { color: textColor }]}>Profile visibility</Text>
        <Text style={[styles.cardText, { color: mutedColor }]}>
          Recruiters can only view your public profile details when this setting is enabled. Recommendations stay available either way.
        </Text>
        <View style={styles.row}>
          <Text style={[styles.rowLabel, { color: textColor }]}>
            Hiring employers can find you
          </Text>
          <Switch
            value={isVisible}
            disabled={savingVisibility}
            onValueChange={(value) => {
              void handleVisibilityChange(value);
            }}
            trackColor={{ false: borderColor, true: tintColor }}
            thumbColor="#ffffff"
          />
        </View>
        <Text style={[styles.note, { color: mutedColor }]}>
          {savingVisibility
            ? 'Saving visibility...'
            : isVisible
              ? 'Your profile can appear to organizations looking for candidates.'
              : 'Your profile stays private for recruiters, but your account and recommendations remain active.'}
        </Text>
      </View>

      <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
        <Text style={[styles.cardTitle, { color: textColor }]}>Account</Text>
        <View style={styles.metaBlock}>
          <Text style={[styles.metaLabel, { color: mutedColor }]}>Email</Text>
          <Text style={[styles.metaValue, { color: textColor }]}>
            {user?.email || user?.username || 'Unavailable'}
          </Text>
        </View>
        <View style={styles.metaBlock}>
          <Text style={[styles.metaLabel, { color: mutedColor }]}>Onboarding</Text>
          <Text style={[styles.metaValue, { color: textColor }]}>
            {user?.profil?.onboarding_completed ? 'Completed' : 'Not completed'}
          </Text>
        </View>
      </View>

      {error ? (
        <View style={[styles.feedbackCard, { borderColor: '#fecaca', backgroundColor: '#fef2f2' }]}>
          <Text style={[styles.feedbackTitle, { color: '#991b1b' }]}>Unable to update settings</Text>
          <Text style={[styles.feedbackText, { color: '#991b1b' }]}>{error}</Text>
        </View>
      ) : null}

      {successMessage ? (
        <View style={[styles.feedbackCard, { borderColor: '#bbf7d0', backgroundColor: '#f0fdf4' }]}>
          <Text style={[styles.feedbackTitle, { color: '#166534' }]}>Settings updated</Text>
          <Text style={[styles.feedbackText, { color: '#166534' }]}>{successMessage}</Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    gap: 16,
    paddingBottom: 36,
  },
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '800',
  },
  cardText: {
    fontSize: 14,
    lineHeight: 20,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  rowLabel: {
    flex: 1,
    fontSize: 15,
    fontWeight: '700',
  },
  note: {
    fontSize: 13,
    lineHeight: 18,
  },
  metaBlock: {
    gap: 4,
  },
  metaLabel: {
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  metaValue: {
    fontSize: 14,
    lineHeight: 20,
  },
  feedbackCard: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    gap: 4,
  },
  feedbackTitle: {
    fontSize: 14,
    fontWeight: '800',
  },
  feedbackText: {
    fontSize: 13,
    lineHeight: 18,
  },
});
