import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';

import { useThemeColor } from '@/hooks/use-theme-color';
import { useAuth } from '@/src/context/AuthContext';

export default function DashboardScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const handleLogout = async () => {
    await logout();
    router.replace('/login');
  };

  const handleOpenOpportunities = () => {
    router.push('/opportunities');
  };

  return (
    <View style={[styles.container, { backgroundColor }]}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={[styles.greeting, { color: mutedColor }]}>
            {user?.email ?? 'Welcome back'}
          </Text>
          <Text style={[styles.title, { color: textColor }]}>Dashboard</Text>
        </View>
        <TouchableOpacity onPress={handleLogout} activeOpacity={0.7}>
          <Text style={[styles.logoutText, { color: tintColor }]}>Logout</Text>
        </TouchableOpacity>
      </View>

      {/* Stats placeholder */}
      <View style={styles.statsRow}>
        {['Applications', 'Saved', 'Views'].map((label) => (
          <View key={label} style={[styles.statCard, { backgroundColor: cardColor, borderColor }]}>
            <Text style={[styles.statValue, { color: textColor }]}>0</Text>
            <Text style={[styles.statLabel, { color: mutedColor }]}>{label}</Text>
          </View>
        ))}
      </View>

      {/* Recent activity placeholder */}
      <View style={[styles.section, { backgroundColor: cardColor, borderColor }]}>
        <Text style={[styles.sectionTitle, { color: textColor }]}>Recent Opportunities</Text>
        <Text style={[styles.emptyText, { color: mutedColor }]}>
          Explore live opportunities from BidWise sources.
        </Text>
        <TouchableOpacity
          style={[styles.primaryButton, { backgroundColor: tintColor }]}
          onPress={handleOpenOpportunities}
          activeOpacity={0.8}
        >
          <Text style={styles.primaryButtonText}>Browse opportunities</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 60,
    paddingHorizontal: 24,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 32,
  },
  greeting: {
    fontSize: 14,
    marginBottom: 4,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 13,
  },
  section: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    textAlign: 'center',
    paddingTop: 20,
    paddingBottom: 16,
  },
  primaryButton: {
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '600',
  },
});
