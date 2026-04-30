import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';

import { AuthProvider } from '@/src/features/auth/context/AuthContext';
import { ThemeModeProvider, useThemeMode } from '@/src/shared/context/ThemeModeContext';

const navigationThemes = {
  light: {
    ...DefaultTheme,
    colors: {
      ...DefaultTheme.colors,
      primary: '#2563eb',
      background: '#ffffff',
      card: '#ffffff',
      text: '#111827',
      border: '#e5e7eb',
      notification: '#2563eb',
    },
  },
  dark: {
    ...DarkTheme,
    colors: {
      ...DarkTheme.colors,
      primary: '#60a5fa',
      background: '#0f172a',
      card: '#111827',
      text: '#f9fafb',
      border: '#374151',
      notification: '#60a5fa',
    },
  },
};

function RootLayoutContent() {
  const { colorScheme } = useThemeMode();

  return (
    <AuthProvider>
      <ThemeProvider value={navigationThemes[colorScheme]}>
        <Stack screenOptions={{ headerShown: false }} />
        <StatusBar style={colorScheme === 'dark' ? 'light' : 'dark'} />
      </ThemeProvider>
    </AuthProvider>
  );
}

export default function RootLayout() {
  return (
    <ThemeModeProvider>
      <RootLayoutContent />
    </ThemeModeProvider>
  );
}
