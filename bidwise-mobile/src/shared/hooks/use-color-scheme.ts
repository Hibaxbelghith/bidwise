import { useThemeMode } from '@/src/shared/context/ThemeModeContext';

export function useColorScheme() {
  return useThemeMode().colorScheme;
}
