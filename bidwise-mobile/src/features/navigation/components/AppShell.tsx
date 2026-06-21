import { type ReactNode, useEffect, useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import AppDrawerContent from './AppDrawerContent';
import AppHeader from './AppHeader';
import MobileTabBar, { type AppTabKey } from './MobileTabBar';

type AppShellProps = {
  children: ReactNode;
  title: string;
  currentTab?: AppTabKey;
  showSearch?: boolean;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  showBackButton?: boolean;
};

const TAB_ROUTES: Record<AppTabKey, '/explore' | '/for-you' | '/dashboard' | '/profile'> = {
  explore: '/explore',
  'for-you': '/for-you',
  dashboard: '/dashboard',
  profile: '/profile',
};

function isCallsForTenderOnlyProfile(profile?: { opportunity_types?: string[] } | null) {
  const types = Array.isArray(profile?.opportunity_types) ? profile.opportunity_types : [];
  return types.length === 1 && types[0] === 'CALLS_FOR_TENDER';
}

export default function AppShell({
  children,
  title,
  currentTab,
  showSearch = false,
  searchValue = '',
  onSearchChange,
  showBackButton = false,
}: AppShellProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');

  const drawerName = useMemo(() => {
    const firstName = String(user?.profil?.prenom || '').trim();
    const lastName = String(user?.profil?.nom || '').trim();
    return [firstName, lastName].filter(Boolean).join(' ') || '';
  }, [user?.profil?.nom, user?.profil?.prenom]);

  const drawerEmail = useMemo(() => {
    return String(user?.email || user?.username || '').trim();
  }, [user?.email, user?.username]);

  const tenderOnly = isCallsForTenderOnlyProfile(user?.profil);
  const isGuestRestrictedTab = !user && Boolean(currentTab) && currentTab !== 'explore';
  const isTenderRestrictedTab = tenderOnly && currentTab === 'for-you';

  useEffect(() => {
    if (isGuestRestrictedTab) {
      router.replace('/explore');
    }
  }, [isGuestRestrictedTab, router]);

  useEffect(() => {
    if (isTenderRestrictedTab) {
      router.replace('/explore');
    }
  }, [isTenderRestrictedTab, router]);

  useEffect(() => {
    if (!user && drawerOpen) {
      setDrawerOpen(false);
    }
  }, [drawerOpen, user]);

  const drawerActions = useMemo(() => {
    return [
      {
        key: 'settings',
        label: 'Settings',
        icon: 'settings-outline' as const,
        onPress: () => {
          setDrawerOpen(false);
          router.push('/settings');
        },
      },
      {
        key: 'support',
        label: 'Help & Support',
        icon: 'help-circle-outline' as const,
        onPress: () => {
          setDrawerOpen(false);
          router.push('/support');
        },
      },
      {
        key: 'logout',
        label: 'Logout',
        icon: 'log-out-outline' as const,
        danger: true,
        onPress: async () => {
          setDrawerOpen(false);
          await logout();
          router.replace('/login');
        },
      },
    ];
  }, [logout, router]);

  if (isGuestRestrictedTab || isTenderRestrictedTab) {
    return <View style={[styles.screen, { backgroundColor }]} />;
  }

  return (
    <View style={[styles.screen, { backgroundColor }]}>
      <AppHeader
        title={title}
        showSearch={showSearch}
        searchValue={searchValue}
        onSearchChange={onSearchChange}
        onMenuPress={user ? () => setDrawerOpen(true) : undefined}
        showBackButton={showBackButton}
        onBackPress={() => router.back()}
        backgroundColor={backgroundColor}
        borderColor={borderColor}
        cardColor={cardColor}
        textColor={textColor}
        mutedColor={mutedColor}
        tintColor={tintColor}
      />

      <View style={styles.content}>{children}</View>

      {currentTab ? (
        <MobileTabBar
          currentTab={currentTab}
          onTabPress={(tab) => {
            if (tab === currentTab) return;
            if (!user && tab !== 'explore') {
              router.push('/login');
              return;
            }
            router.replace(TAB_ROUTES[tab]);
          }}
          isAuthenticated={Boolean(user)}
          hideForYou={tenderOnly}
          backgroundColor={backgroundColor}
          borderColor={borderColor}
          cardColor={cardColor}
          textColor={textColor}
          mutedColor={mutedColor}
          tintColor={tintColor}
        />
      ) : null}

      {drawerOpen && user ? (
        <View style={styles.drawerOverlay}>
          <Pressable style={styles.drawerScrim} onPress={() => setDrawerOpen(false)} />
          <AppDrawerContent
            name={drawerName}
            email={drawerEmail}
            backgroundColor={backgroundColor}
            borderColor={borderColor}
            cardColor={cardColor}
            textColor={textColor}
            mutedColor={mutedColor}
            tintColor={tintColor}
            actions={drawerActions}
          />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  drawerOverlay: {
    ...StyleSheet.absoluteFillObject,
    flexDirection: 'row',
  },
  drawerScrim: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.36)',
  },
});
