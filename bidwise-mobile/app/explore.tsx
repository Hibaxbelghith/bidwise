import ExploreScreen from '@/src/features/explore/components/ExploreScreen';
import { useExploreScreen } from '@/src/features/explore/hooks/useExploreScreen';
import AppShell from '@/src/features/navigation/components/AppShell';

export default function ExploreRoute() {
  const {
    searchInput,
    setSearchInput,
    ...exploreScreen
  } = useExploreScreen();

  return (
    <AppShell
      title="Explore"
      currentTab="explore"
      showSearch
      searchValue={searchInput}
      onSearchChange={setSearchInput}
    >
      <ExploreScreen {...exploreScreen} />
    </AppShell>
  );
}
