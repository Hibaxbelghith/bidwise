import { useMemo } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { type Href, useRouter } from 'expo-router';

import ProfileSection from '@/src/features/profile/components/ProfileSection';
import ResumeSection from '@/src/features/profile/components/ResumeSection';
import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';
import type { BidWiseProfile, ProfileUser } from '@/src/features/profile/types';
import {
  ONBOARDING_OPPORTUNITY_TYPE_OPTIONS,
  OPPORTUNITY_TYPE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';
import {
  normalizeInterestList,
  normalizeLocations,
  normalizeOptionValues,
  normalizeSkillList,
  normalizeTextList,
} from '@/src/features/profile/utils/profileValidation';

const formatPreference = (value: unknown) => {
  const normalized = String(value || '').trim();
  if (!normalized) return '';

  return normalized
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

const formatList = (value: unknown) => normalizeTextList(value).map(formatPreference);

const formatSalary = (profile?: BidWiseProfile) => {
  const min = profile?.compensation_min_expectation;
  const max = profile?.compensation_max_expectation;
  if (min || max) {
    if (min && max) return `${min} - ${max} ${profile?.compensation_currency || 'TND'} / month`;
    return `${min || max} ${profile?.compensation_currency || 'TND'} / month`;
  }
  if (!profile?.compensation_expectation) return 'Not specified';
  const period = formatPreference(profile.compensation_period || 'MONTHLY').toLowerCase();
  return `${profile.compensation_expectation} ${profile.compensation_currency || 'TND'} / ${period}`;
};

const formatOpportunityTypes = (value: unknown) => {
  const selected = new Set(normalizeOptionValues(value, OPPORTUNITY_TYPE_OPTIONS));
  return ONBOARDING_OPPORTUNITY_TYPE_OPTIONS
    .filter((option) => option.values.every((item) => selected.has(item)))
    .map((option) => option.label);
};

export default function ProfileScreen() {
  const router = useRouter();
  const { user, loadUserProfile, loading } = useAuth();
  const typedUser = user as ProfileUser | null;
  const profile = typedUser?.profil;

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');
  const sectionColors = useMemo(
    () => ({ card: cardColor, border: borderColor, text: textColor, muted: mutedColor }),
    [borderColor, cardColor, mutedColor, textColor],
  );
  const controlColors = useMemo(
    () => ({ tint: tintColor, border: borderColor, text: textColor, muted: mutedColor, card: cardColor }),
    [borderColor, cardColor, mutedColor, textColor, tintColor],
  );

  const completion = profile?.profile_completion || { score: 0, missing: [] };
  const missing = Array.isArray(completion.missing) ? completion.missing.slice(0, 3) : [];
  const displayName = [profile?.prenom, profile?.nom].filter(Boolean).join(' ') || typedUser?.email || 'BidWise profile';
  const hasProfileData = Boolean(
    profile?.target_roles?.length
      || profile?.competences?.length
      || profile?.domaines_interet?.length
      || profile?.preferred_locations?.length,
  );

  const renderChips = (items: string[]) => {
    if (!items.length) {
      return <Text style={[styles.emptyText, { color: mutedColor }]}>Not specified</Text>;
    }

    return (
      <View style={styles.chipWrap}>
        {items.map((item) => (
          <View key={item} style={[styles.chip, { borderColor: tintColor, backgroundColor: tintColor + '14' }]}>
            <Text style={[styles.chipText, { color: tintColor }]}>{item}</Text>
          </View>
        ))}
      </View>
    );
  };

  const openOnboarding = () => {
    router.push('/onboarding' as Href);
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor }]}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={loadUserProfile} tintColor={tintColor} />}
    >
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={[styles.eyebrow, { color: tintColor }]}>Recommendation-ready profile</Text>
          <Text style={[styles.title, { color: textColor }]}>{displayName}</Text>
          <Text style={[styles.subtitle, { color: mutedColor }]}>
            Keep your signals clean so matching stays precise.
          </Text>
        </View>
        <TouchableOpacity activeOpacity={0.75} onPress={openOnboarding} style={[styles.editButton, { backgroundColor: tintColor }]}>
          <Text style={styles.editButtonText}>{hasProfileData ? 'Edit' : 'Start'}</Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.completionCard, { backgroundColor: cardColor, borderColor }]}>
        <View style={styles.completionTop}>
          <Text style={[styles.completionScore, { color: textColor }]}>{completion.score}% complete</Text>
          <Text style={[styles.completionHint, { color: mutedColor }]}>
            {missing.length ? `Next: ${missing.join(', ')}` : 'Core matching signals are present.'}
          </Text>
        </View>
        <View style={[styles.progressTrack, { backgroundColor: borderColor }]}>
          <View
            style={[
              styles.progressFill,
              { backgroundColor: tintColor, width: `${Math.min(Math.max(completion.score || 0, 0), 100)}%` },
            ]}
          />
        </View>
      </View>

      <ProfileSection
        title="Basic Information"
        description="Identity and experience level."
        defaultOpen
        colors={sectionColors}
      >
        <View style={styles.infoGrid}>
          <InfoItem label="First name" value={profile?.prenom || 'Not specified'} muted={mutedColor} text={textColor} />
          <InfoItem label="Last name" value={profile?.nom || 'Not specified'} muted={mutedColor} text={textColor} />
          <InfoItem label="Experience" value={formatPreference(profile?.niveau_experience) || 'Not specified'} muted={mutedColor} text={textColor} />
          <InfoItem label="Years" value={profile?.annees_experience != null ? String(profile.annees_experience) : 'Not specified'} muted={mutedColor} text={textColor} />
        </View>
      </ProfileSection>

      <ProfileSection
        title="Work Preferences"
        description="Location, mode, contract and compensation."
        defaultOpen
        colors={sectionColors}
      >
        <InfoItem label="Salary" value={formatSalary(profile)} muted={mutedColor} text={textColor} />
        <InfoItem label="Locations" value={normalizeLocations(profile?.preferred_locations).join(', ') || 'Not specified'} muted={mutedColor} text={textColor} />
        <View style={styles.block}>
          <Text style={[styles.blockLabel, { color: mutedColor }]}>Opportunity types</Text>
          {renderChips(formatOpportunityTypes(profile?.opportunity_types))}
        </View>
        <View style={styles.block}>
          <Text style={[styles.blockLabel, { color: mutedColor }]}>Work modes</Text>
          {renderChips(formatList(profile?.work_mode_preferences))}
        </View>
        <View style={styles.block}>
          <Text style={[styles.blockLabel, { color: mutedColor }]}>Employment types</Text>
          {renderChips(formatList(profile?.employment_types))}
        </View>
      </ProfileSection>

      <ProfileSection
        title="Career Signals"
        description="Skills, target roles and industries."
        defaultOpen
        colors={sectionColors}
      >
        <View style={styles.block}>
          <Text style={[styles.blockLabel, { color: mutedColor }]}>Target roles</Text>
          {renderChips(normalizeTextList(profile?.target_roles))}
        </View>
        <View style={styles.block}>
          <Text style={[styles.blockLabel, { color: mutedColor }]}>Skills</Text>
          {renderChips(normalizeSkillList(profile?.competences))}
        </View>
        <View style={styles.block}>
          <Text style={[styles.blockLabel, { color: mutedColor }]}>Industries / Interests</Text>
          {renderChips(normalizeInterestList(profile?.domaines_interet))}
        </View>
      </ProfileSection>

      <ProfileSection
        title="Resume / CV"
        description="Upload a resume or preview a BidWise resume draft."
        defaultOpen
        colors={sectionColors}
      >
        <ResumeSection profile={profile} onChanged={loadUserProfile} colors={controlColors} />
      </ProfileSection>

      <ProfileSection
        title="Profile Settings"
        description="Visibility and future recommendation controls."
        defaultOpen={false}
        colors={sectionColors}
      >
        <InfoItem
          label="Visibility"
          value={profile?.profile_visibility === false ? 'Hidden' : 'Visible to recruiters'}
          muted={mutedColor}
          text={textColor}
        />
        <InfoItem
          label="Onboarding"
          value={profile?.onboarding_completed ? 'Completed' : 'Not completed'}
          muted={mutedColor}
          text={textColor}
        />
        <Text style={[styles.settingsNote, { color: mutedColor }]}>
          Future match tuning controls will live here when recommendation settings are introduced.
        </Text>
      </ProfileSection>
    </ScrollView>
  );
}

function InfoItem({ label, value, muted, text }: { label: string; value: string; muted: string; text: string }) {
  return (
    <View style={styles.infoItem}>
      <Text style={[styles.infoLabel, { color: muted }]}>{label}</Text>
      <Text style={[styles.infoValue, { color: value === 'Not specified' ? muted : text }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    gap: 16,
    padding: 16,
    paddingBottom: 40,
    paddingTop: 58,
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 14,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: '800',
    marginBottom: 6,
    textTransform: 'uppercase',
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 20,
  },
  editButton: {
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 11,
  },
  editButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
  completionCard: {
    borderRadius: 14,
    borderWidth: 1,
    gap: 12,
    padding: 16,
  },
  completionTop: {
    gap: 4,
  },
  completionScore: {
    fontSize: 18,
    fontWeight: '800',
  },
  completionHint: {
    fontSize: 13,
    lineHeight: 18,
  },
  progressTrack: {
    borderRadius: 999,
    height: 8,
    overflow: 'hidden',
  },
  progressFill: {
    borderRadius: 999,
    height: '100%',
  },
  infoGrid: {
    gap: 12,
  },
  infoItem: {
    gap: 4,
  },
  infoLabel: {
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  infoValue: {
    fontSize: 15,
    lineHeight: 21,
  },
  block: {
    gap: 8,
  },
  blockLabel: {
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  chipText: {
    fontSize: 13,
    fontWeight: '700',
  },
  emptyText: {
    fontSize: 13,
    fontStyle: 'italic',
  },
  settingsNote: {
    fontSize: 13,
    lineHeight: 19,
  },
});
