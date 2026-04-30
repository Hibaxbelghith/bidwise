import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { type Href, useRouter } from 'expo-router';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

const PROFILE_STORAGE_KEY = 'bidwise_user_profile';

type StoredProfile = {
  target_roles?: unknown;
  employment_types?: unknown;
  remote_preference?: unknown;
};

const toStringArray = (value: unknown) => {
  if (!Array.isArray(value)) return [];

  return value
    .map((item) => String(item || '').trim())
    .filter(Boolean);
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

export default function ProfileScreen() {
  const router = useRouter();
  const [targetRoles, setTargetRoles] = useState<string[]>([]);
  const [employmentTypes, setEmploymentTypes] = useState<string[]>([]);
  const [remotePreference, setRemotePreference] = useState('');

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const hasProfileData = targetRoles.length > 0 || employmentTypes.length > 0 || remotePreference;

  const handleOpenOnboarding = () => {
    router.push('/onboarding' as Href);
  };

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const storedProfile = await AsyncStorage.getItem(PROFILE_STORAGE_KEY);
        const parsed = storedProfile ? (JSON.parse(storedProfile) as StoredProfile) : null;

        setTargetRoles(toStringArray(parsed?.target_roles));
        setEmploymentTypes(toStringArray(parsed?.employment_types));
        setRemotePreference(formatPreference(parsed?.remote_preference));
      } catch {
        setTargetRoles([]);
        setEmploymentTypes([]);
        setRemotePreference('');
      }
    };

    loadProfile();
  }, []);

  const renderChips = (items: string[]) => {
    if (!items.length) {
      return <Text style={[styles.emptyText, { color: mutedColor }]}>Not specified</Text>;
    }

    return (
      <View style={styles.chipWrap}>
        {items.map((item) => (
          <View key={item} style={[styles.chip, { borderColor: tintColor, backgroundColor: cardColor }]}>
            <Text style={[styles.chipText, { color: tintColor }]}>{item}</Text>
          </View>
        ))}
      </View>
    );
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor }]}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <Text style={[styles.title, { color: textColor }]}>My Profile</Text>

      {!hasProfileData ? (
        <TouchableOpacity
          style={[styles.card, { backgroundColor: cardColor, borderColor }]}
          onPress={handleOpenOnboarding}
          activeOpacity={0.8}
        >
          <Text style={[styles.sectionTitle, { color: textColor }]}>Complete onboarding</Text>
          <Text style={[styles.description, { color: mutedColor }]}>
            Add your preferences to personalize your BidWise experience.
          </Text>
        </TouchableOpacity>
      ) : null}

      <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
        <Text style={[styles.sectionTitle, { color: textColor }]}>Target roles</Text>
        {renderChips(targetRoles)}
      </View>

      <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
        <Text style={[styles.sectionTitle, { color: textColor }]}>Employment types</Text>
        {renderChips(employmentTypes)}
      </View>

      <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
        <Text style={[styles.sectionTitle, { color: textColor }]}>Remote preference</Text>
        <Text style={[styles.valueText, { color: remotePreference ? textColor : mutedColor }]}>
          {remotePreference || 'Not specified'}
        </Text>
      </View>

      <TouchableOpacity style={[styles.editButton, { backgroundColor: tintColor }]} activeOpacity={0.8}>
        <Text style={styles.editButtonText}>Edit Profile</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: 16,
    paddingTop: 60,
    gap: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 8,
  },
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 10,
  },
  description: {
    fontSize: 14,
    lineHeight: 20,
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  chipText: {
    fontSize: 13,
    fontWeight: '600',
  },
  valueText: {
    fontSize: 15,
    lineHeight: 22,
  },
  emptyText: {
    fontSize: 14,
    fontStyle: 'italic',
  },
  editButton: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 4,
  },
  editButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
});
