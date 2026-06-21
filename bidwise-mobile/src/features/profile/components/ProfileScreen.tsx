import { useMemo } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { type Href, useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import ProfileSectionLinkCard from '@/src/features/profile/components/ProfileSectionLinkCard';
import type { BidWiseProfile, ProfileUser } from '@/src/features/profile/types';
import {
  ONBOARDING_OPPORTUNITY_TYPE_OPTIONS,
  OPPORTUNITY_TYPE_OPTIONS,
} from '@/src/features/profile/constants/profileOptions';
import {
  formatBusinessFamilyLabels,
  normalizeLocations,
  normalizeOptionValues,
  normalizeSkillList,
  normalizeTextList,
} from '@/src/features/profile/utils/profileValidation';
import { EXPERIENCE_LEVEL_OPTIONS } from '@/src/features/profile/utils/profileEditorState';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

type ProfileScreenProps = {
  embedded?: boolean;
};

const formatPreference = (value: unknown) => {
  const normalized = String(value || '').trim();
  if (!normalized) return '';

  return normalized
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

const EXPERIENCE_LEVEL_LABELS = Object.fromEntries(
  EXPERIENCE_LEVEL_OPTIONS.map((option) => [option.value, option.label.replace(/\s*\(.+\)$/, '')]),
) as Record<string, string>;

const PROFILE_COMPLETION_LABELS: Record<string, string> = {
  first_name: 'first name',
  last_name: 'last name',
  experience_level: 'experience level',
  years_experience: 'years of experience',
  locations: 'locations',
  work_modes: 'work modes',
  employment_types: 'employment types',
  opportunity_types: 'opportunity types',
  skills: 'skills',
  target_roles: 'target roles',
  interests: 'sectors',
  resume: 'resume',
};

const formatOpportunityTypes = (value: unknown) => {
  const selected = new Set(normalizeOptionValues(value, OPPORTUNITY_TYPE_OPTIONS));
  return ONBOARDING_OPPORTUNITY_TYPE_OPTIONS
    .filter((option) => option.values.every((item) => selected.has(item)))
    .map((option) => option.label);
};

const summarizeList = (items: string[], fallback: string) => {
  if (!items.length) return fallback;
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} • ${items[1]}`;
  return `${items[0]} • ${items[1]} +${items.length - 2}`;
};

const formatSalarySummary = (profile?: BidWiseProfile) => {
  const min = profile?.compensation_min_expectation;
  const max = profile?.compensation_max_expectation;
  const currency = profile?.compensation_currency || 'TND';

  if (min != null && max != null) return `${min}-${max} ${currency}`;
  if (min != null) return `From ${min} ${currency}`;
  if (max != null) return `Up to ${max} ${currency}`;
  if (profile?.compensation_expectation != null) return `${profile.compensation_expectation} ${currency}`;
  return 'Salary not set';
};

const isTenderOnlyProfile = (profile?: BidWiseProfile) => {
  const types = normalizeOptionValues(profile?.opportunity_types, OPPORTUNITY_TYPE_OPTIONS);
  return types.length === 1 && types[0] === 'CALLS_FOR_TENDER';
};

export default function ProfileScreen({ embedded = false }: ProfileScreenProps) {
  const router = useRouter();
  const { user } = useAuth();
  const typedUser = user as ProfileUser | null;
  const profile = typedUser?.profil;

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const completion = profile?.profile_completion || { score: 0, missing: [] };
  const tenderOnly = isTenderOnlyProfile(profile);
  const displayName =
    [profile?.prenom, profile?.nom].filter(Boolean).join(' ')
    || typedUser?.email
    || 'BidWise profile';
  const subtitle =
    typedUser?.email
    || (tenderOnly
      ? 'Keep your public tender filters simple and clear.'
      : 'Keep your signals clear so matching and recruiter discovery stay accurate.');

  const basicSummary = useMemo(() => {
    const nameSummary = [profile?.prenom, profile?.nom].filter(Boolean).join(' ').trim() || 'Add your name';
    if (tenderOnly) return nameSummary;
    const normalizedExperience = String(profile?.niveau_experience || '').trim().toUpperCase();
    const experience = EXPERIENCE_LEVEL_LABELS[normalizedExperience]
      || formatPreference(profile?.niveau_experience)
      || 'Experience not set';
    const years =
      profile?.annees_experience != null ? `${profile.annees_experience} year(s)` : 'Years not set';
    return `${nameSummary} • ${experience} • ${years}`;
  }, [profile?.annees_experience, profile?.niveau_experience, profile?.nom, profile?.prenom, tenderOnly]);

  const preferencesSummary = useMemo(() => {
    const types = summarizeList(formatOpportunityTypes(profile?.opportunity_types), 'Opportunity types not set');
    const locations = summarizeList(normalizeLocations(profile?.preferred_locations), 'Locations not set');
    if (tenderOnly) return `${types} - ${locations}`;
    return `${types} • ${locations} • ${formatSalarySummary(profile)}`;
  }, [profile, tenderOnly]);

  const careerSummary = useMemo(() => {
    const roles = summarizeList(normalizeTextList(profile?.target_roles), 'Roles not set');
    const skills = summarizeList(normalizeSkillList(profile?.competences), 'Skills not set');
    const interests = summarizeList(formatBusinessFamilyLabels(profile?.domaines_interet), 'Sectors not set');
    return `${roles} • ${skills} • ${interests}`;
  }, [profile?.competences, profile?.domaines_interet, profile?.target_roles]);

  const resumeSummary = profile?.active_resume?.metadata?.original_filename
    || (profile?.active_resume ? 'Resume uploaded' : 'No resume uploaded yet');

  const settingsSummary = profile?.profile_visibility === false
    ? 'Private to recruiters'
    : 'Visible to recruiters';

  const missing = Array.isArray(completion.missing)
    ? completion.missing
      .filter((item) => !tenderOnly || ['first_name', 'last_name', 'opportunity_types'].includes(item))
      .slice(0, 3)
      .map((item) => PROFILE_COMPLETION_LABELS[item] || formatPreference(item))
    : [];

  const openRoute = (route: string) => {
    router.push(route as Href);
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor }]}
      contentContainerStyle={[styles.content, embedded ? styles.embeddedContent : null]}
      showsVerticalScrollIndicator={false}
    >
      <View style={[styles.heroCard, { backgroundColor: cardColor, borderColor }]}>
        <View style={styles.identityText}>
          <Text style={[styles.profileName, { color: textColor }]}>{displayName}</Text>
          <Text style={[styles.profileSubtitle, { color: mutedColor }]} numberOfLines={2}>
            {subtitle}
          </Text>
        </View>

        <View style={[styles.completionCard, { backgroundColor, borderColor }]}>
          <View style={styles.completionTop}>
            <Text style={[styles.completionScore, { color: textColor }]}>{completion.score}% complete</Text>
            <Text style={[styles.completionHint, { color: mutedColor }]}>
              {missing.length
                ? `Next: ${missing.join(', ')}`
                : tenderOnly
                  ? 'Your tender profile is ready.'
                  : 'Your main profile signals are ready.'}
            </Text>
          </View>
          <View style={[styles.progressTrack, { backgroundColor: borderColor }]}>
            <View
              style={[
                styles.progressFill,
                {
                  backgroundColor: tintColor,
                  width: `${Math.min(Math.max(completion.score || 0, 0), 100)}%`,
                },
              ]}
            />
          </View>
        </View>
      </View>

      <View style={styles.sectionList}>
        <ProfileSectionLinkCard
          title="Basic information"
          description={tenderOnly ? 'Name and email.' : 'Name and experience level.'}
          summary={basicSummary}
          onPress={() => openRoute('/profile-basic')}
        />
        <ProfileSectionLinkCard
          title={tenderOnly ? 'Tender preferences' : 'Preferences'}
          description={tenderOnly ? 'Opportunity type and preferred regions.' : 'Locations, work mode, and salary.'}
          summary={preferencesSummary}
          onPress={() => openRoute('/profile-preferences')}
        />
        {!tenderOnly ? (
        <ProfileSectionLinkCard
          title="Career signals"
          description="Roles, skills, and sectors."
          summary={careerSummary}
          onPress={() => openRoute('/profile-career')}
        />
        ) : null}
        {!tenderOnly ? (
        <ProfileSectionLinkCard
          title="Resume"
          description="CV used for applications and AI extraction."
          summary={resumeSummary}
          onPress={() => openRoute('/profile-resume')}
        />
        ) : null}
        {!tenderOnly ? (
        <ProfileSectionLinkCard
          title="Settings"
          description="Recruiter visibility and account status."
          summary={settingsSummary}
          onPress={() => openRoute('/settings')}
        />
        ) : null}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    gap: 16,
    padding: 16,
    paddingBottom: 36,
  },
  embeddedContent: {
    paddingTop: 16,
  },
  heroCard: {
    borderRadius: 22,
    borderWidth: 1,
    gap: 16,
    padding: 18,
  },
  identityText: {
    gap: 4,
  },
  profileName: {
    fontSize: 22,
    fontWeight: '800',
  },
  profileSubtitle: {
    fontSize: 13,
    lineHeight: 19,
  },
  completionCard: {
    borderRadius: 18,
    borderWidth: 1,
    gap: 12,
    padding: 14,
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
  sectionList: {
    gap: 12,
  },
});
