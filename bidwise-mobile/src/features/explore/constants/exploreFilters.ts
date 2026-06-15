import type { OpportunityTypeFilter } from '@/src/features/opportunities/hooks/useOpportunitiesList';
import type { OpportunitySource } from '@/src/features/opportunities/services/opportunitiesService';

export type ExploreFilterOption = {
  value: OpportunityTypeFilter;
  label: string;
};

export type ExploreChipOption<T extends string> = {
  value: T;
  label: string;
};

export const EXPLORE_TYPE_FILTERS: ExploreFilterOption[] = [
  { value: 'ALL', label: 'All' },
  { value: 'EMPLOI', label: 'Jobs' },
  { value: 'STAGE', label: 'Internships' },
  { value: 'SAISONNIER', label: 'Seasonal' },
  { value: 'PROJET', label: 'Tenders' },
];

export const EXPLORE_WORK_MODE_FILTERS: ExploreChipOption<'' | 'REMOTE' | 'HYBRID' | 'ON_SITE'>[] = [
  { value: '', label: 'Any mode' },
  { value: 'REMOTE', label: 'Remote' },
  { value: 'HYBRID', label: 'Hybrid' },
  { value: 'ON_SITE', label: 'On site' },
];

export const EXPLORE_DATE_POSTED_FILTERS: ExploreChipOption<
  '' | 'day' | '3days' | 'week' | '2weeks' | 'month'
>[] = [
  { value: '', label: 'Any time' },
  { value: 'day', label: '24h' },
  { value: '3days', label: '3 days' },
  { value: 'week', label: '1 week' },
  { value: '2weeks', label: '2 weeks' },
  { value: 'month', label: '1 month' },
];

export function buildExploreSourceFilters(sourceOptions: OpportunitySource[]) {
  const priorityOrder = ['BidWise Organizations', 'LinkedIn', 'Keejob', 'EmploiTunisie', 'MarchesPublics'];
  const priorityIndex = new Map(priorityOrder.map((label, index) => [label.toLowerCase(), index]));

  const options = sourceOptions
    .slice()
    .sort((left, right) => {
      const leftKey = String(left.nom || '').trim().toLowerCase();
      const rightKey = String(right.nom || '').trim().toLowerCase();
      const leftPriority = priorityIndex.get(leftKey);
      const rightPriority = priorityIndex.get(rightKey);

      if (leftPriority !== undefined && rightPriority !== undefined) {
        return leftPriority - rightPriority;
      }
      if (leftPriority !== undefined) return -1;
      if (rightPriority !== undefined) return 1;
      return leftKey.localeCompare(rightKey);
    })
    .slice(0, 6)
    .map((source) => ({
      value: String(source.id),
      label: source.nom,
    }));

  return [{ value: '', label: 'All sources' }, ...options];
}
