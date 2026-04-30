import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

type AppColorScheme = 'light' | 'dark';

type ThemeModeContextValue = {
  colorScheme: AppColorScheme;
  isDark: boolean;
  setColorScheme: (colorScheme: AppColorScheme) => void;
  toggleColorScheme: () => void;
};

const THEME_STORAGE_KEY = 'bidwise_mobile_theme';

const ThemeModeContext = createContext<ThemeModeContextValue | null>(null);

const fallbackThemeMode: ThemeModeContextValue = {
  colorScheme: 'light',
  isDark: false,
  setColorScheme: () => {},
  toggleColorScheme: () => {},
};

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [colorScheme, setColorSchemeState] = useState<AppColorScheme>('light');

  useEffect(() => {
    let isMounted = true;

    const loadStoredTheme = async () => {
      const storedTheme = await AsyncStorage.getItem(THEME_STORAGE_KEY);
      if (!isMounted || (storedTheme !== 'light' && storedTheme !== 'dark')) return;
      setColorSchemeState(storedTheme);
    };

    loadStoredTheme();

    return () => {
      isMounted = false;
    };
  }, []);

  const setColorScheme = useCallback((nextColorScheme: AppColorScheme) => {
    setColorSchemeState(nextColorScheme);
    AsyncStorage.setItem(THEME_STORAGE_KEY, nextColorScheme);
  }, []);

  const toggleColorScheme = useCallback(() => {
    setColorSchemeState((currentColorScheme) => {
      const nextColorScheme = currentColorScheme === 'dark' ? 'light' : 'dark';
      AsyncStorage.setItem(THEME_STORAGE_KEY, nextColorScheme);
      return nextColorScheme;
    });
  }, []);

  const value = useMemo(
    () => ({
      colorScheme,
      isDark: colorScheme === 'dark',
      setColorScheme,
      toggleColorScheme,
    }),
    [colorScheme, setColorScheme, toggleColorScheme]
  );

  return <ThemeModeContext.Provider value={value}>{children}</ThemeModeContext.Provider>;
}

export function useThemeMode() {
  return useContext(ThemeModeContext) ?? fallbackThemeMode;
}
