import { useMemo, useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { TUNISIAN_LOCATION_OPTIONS } from '@/src/features/profile/constants/profileOptions';
import type { OpportunityTypeFilter } from '@/src/features/opportunities/hooks/useOpportunitiesList';
import type { OpportunitySource } from '@/src/features/opportunities/services/opportunitiesService';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

import {
  buildExploreSourceFilters,
  EXPLORE_DATE_POSTED_FILTERS,
  EXPLORE_DEADLINE_FILTERS,
  EXPLORE_TYPE_FILTERS,
  EXPLORE_WORK_MODE_FILTERS,
} from '../constants/exploreFilters';

type ExploreFiltersBarProps = {
  cityInput: string;
  onCityChange: (value: string) => void;
  typeFilter: OpportunityTypeFilter;
  onTypeChange: (value: OpportunityTypeFilter) => void;
  sourceFilter: string;
  onSourceChange: (value: string) => void;
  sourceOptions: OpportunitySource[];
  workModeFilter: '' | 'REMOTE' | 'HYBRID' | 'ON_SITE';
  onWorkModeChange: (value: '' | 'REMOTE' | 'HYBRID' | 'ON_SITE') => void;
  datePostedFilter: '' | 'day' | '3days' | 'week' | '2weeks' | 'month';
  onDatePostedChange: (value: '' | 'day' | '3days' | 'week' | '2weeks' | 'month') => void;
  hasActiveFilters: boolean;
  onClearFilters: () => void;
  totalCount: number;
  cardColor: string;
  borderColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
  tenderOnly?: boolean;
};

type FilterChipProps = {
  label: string;
  selected: boolean;
  onPress: () => void;
  borderColor: string;
  textColor: string;
  tintColor: string;
  cardColor: string;
  compact?: boolean;
};

function FilterChip({
  label,
  selected,
  onPress,
  borderColor,
  textColor,
  tintColor,
  cardColor,
  compact = false,
}: FilterChipProps) {
  return (
    <TouchableOpacity
      activeOpacity={0.8}
      onPress={onPress}
      style={[
        styles.filterChip,
        compact ? styles.filterChipCompact : null,
        {
          borderColor: selected ? tintColor : borderColor,
          backgroundColor: selected ? `${tintColor}16` : cardColor,
        },
      ]}
    >
      <Text numberOfLines={1} style={[styles.filterChipText, { color: selected ? tintColor : textColor }]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

export default function ExploreFiltersBar({
  cityInput,
  onCityChange,
  typeFilter,
  onTypeChange,
  sourceFilter,
  onSourceChange,
  sourceOptions,
  workModeFilter,
  onWorkModeChange,
  datePostedFilter,
  onDatePostedChange,
  hasActiveFilters,
  onClearFilters,
  totalCount,
  cardColor,
  borderColor,
  textColor,
  mutedColor,
  tintColor,
  tenderOnly = false,
}: ExploreFiltersBarProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showCities, setShowCities] = useState(false);
  const backgroundColor = useThemeColor({}, 'background');

  const sourceFilters = useMemo(
    () => buildExploreSourceFilters(sourceOptions).slice(0, 5),
    [sourceOptions],
  );
  const typeFilters = useMemo(() => {
    return tenderOnly
      ? EXPLORE_TYPE_FILTERS.filter((option) => option.value === 'PROJET')
      : EXPLORE_TYPE_FILTERS;
  }, [tenderOnly]);
  const dateFilters = tenderOnly ? EXPLORE_DEADLINE_FILTERS : EXPLORE_DATE_POSTED_FILTERS;

  const selectedSourceLabel = useMemo(() => {
    return sourceFilters.find((option) => option.value === sourceFilter)?.label || 'All sources';
  }, [sourceFilter, sourceFilters]);

  const selectedWorkModeLabel = useMemo(() => {
    return (
      EXPLORE_WORK_MODE_FILTERS.find((option) => option.value === workModeFilter)?.label || 'Any mode'
    );
  }, [workModeFilter]);

  const selectedDatePostedLabel = useMemo(() => {
    return (
      dateFilters.find((option) => option.value === datePostedFilter)?.label ||
      (tenderOnly ? 'Any deadline' : 'Any time')
    );
  }, [dateFilters, datePostedFilter, tenderOnly]);

  const filterSummary = tenderOnly
    ? selectedDatePostedLabel
    : `${selectedWorkModeLabel} · ${selectedDatePostedLabel} · ${selectedSourceLabel}`;

  return (
    <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
      <View style={styles.headerRow}>
        <View>
          <Text style={[styles.resultCount, { color: textColor }]}>{totalCount} opportunities</Text>
        </View>
        {hasActiveFilters ? (
          <TouchableOpacity activeOpacity={0.8} onPress={onClearFilters}>
            <Text style={[styles.clearText, { color: tintColor }]}>Reset</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
        {typeFilters.map((option) => (
          <FilterChip
            key={option.value}
            label={option.label}
            selected={option.value === typeFilter}
            onPress={() => {
              if (!tenderOnly) {
                onTypeChange(option.value);
              }
            }}
            borderColor={borderColor}
            textColor={textColor}
            tintColor={tintColor}
            cardColor={cardColor}
          />
        ))}
      </ScrollView>

      <View style={styles.quickActionsRow}>
        <TouchableOpacity
          activeOpacity={0.82}
          onPress={() => setShowCities((value) => !value)}
          style={[styles.quickFilterButton, { borderColor, backgroundColor }]}
        >
          <Ionicons name="location-outline" size={16} color={mutedColor} />
          <Text numberOfLines={1} style={[styles.quickFilterText, { color: cityInput ? textColor : mutedColor }]}>
            {cityInput || 'City'}
          </Text>
          <Ionicons
            name={showCities ? 'chevron-up-outline' : 'chevron-down-outline'}
            size={16}
            color={mutedColor}
          />
        </TouchableOpacity>

        <TouchableOpacity
          activeOpacity={0.82}
          onPress={() => setShowAdvanced((value) => !value)}
          style={[styles.quickFilterButton, { borderColor, backgroundColor }]}
        >
          <Ionicons name="options-outline" size={16} color={mutedColor} />
          <Text numberOfLines={1} style={[styles.quickFilterText, { color: textColor }]}>
            {tenderOnly ? 'Deadline' : 'More filters'}
          </Text>
          <Ionicons
            name={showAdvanced ? 'chevron-up-outline' : 'chevron-down-outline'}
            size={16}
            color={mutedColor}
          />
        </TouchableOpacity>
      </View>

      {showCities ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filterRow}
        >
          <FilterChip
            label="All cities"
            selected={!cityInput}
            onPress={() => {
              onCityChange('');
              setShowCities(false);
            }}
            borderColor={borderColor}
            textColor={textColor}
            tintColor={tintColor}
            cardColor={cardColor}
            compact
          />
          {TUNISIAN_LOCATION_OPTIONS.map((city) => (
            <FilterChip
              key={city}
              label={city}
              selected={cityInput === city}
              onPress={() => {
                onCityChange(city);
                setShowCities(false);
              }}
              borderColor={borderColor}
              textColor={textColor}
              tintColor={tintColor}
              cardColor={cardColor}
              compact
            />
          ))}
        </ScrollView>
      ) : null}

      {showAdvanced ? (
        <View style={styles.advancedPanel}>
          {!tenderOnly ? (
            <View style={styles.advancedSection}>
              <Text style={[styles.sectionTitle, { color: mutedColor }]}>Work mode</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
                {EXPLORE_WORK_MODE_FILTERS.map((option) => (
                  <FilterChip
                    key={option.value || 'all'}
                    label={option.label}
                    selected={option.value === workModeFilter}
                    onPress={() => onWorkModeChange(option.value)}
                    borderColor={borderColor}
                    textColor={textColor}
                    tintColor={tintColor}
                    cardColor={cardColor}
                    compact
                  />
                ))}
              </ScrollView>
            </View>
          ) : null}

          <View style={styles.advancedSection}>
            <Text style={[styles.sectionTitle, { color: mutedColor }]}>
              {tenderOnly ? 'Deadline' : 'Posted'}
            </Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
              {dateFilters.map((option) => (
                <FilterChip
                  key={option.value || 'all'}
                  label={option.label}
                  selected={option.value === datePostedFilter}
                  onPress={() => onDatePostedChange(option.value)}
                  borderColor={borderColor}
                  textColor={textColor}
                  tintColor={tintColor}
                  cardColor={cardColor}
                  compact
                />
              ))}
            </ScrollView>
          </View>

          {!tenderOnly && sourceFilters.length > 1 ? (
            <View style={styles.advancedSection}>
              <Text style={[styles.sectionTitle, { color: mutedColor }]}>Source</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
                {sourceFilters.map((option) => (
                  <FilterChip
                    key={option.value || 'all'}
                    label={option.label}
                    selected={option.value === sourceFilter}
                    onPress={() => onSourceChange(option.value)}
                    borderColor={borderColor}
                    textColor={textColor}
                    tintColor={tintColor}
                    cardColor={cardColor}
                    compact
                  />
                ))}
              </ScrollView>
            </View>
          ) : null}

          <View style={styles.summaryRow}>
            <Text numberOfLines={1} style={[styles.summaryText, { color: mutedColor }]}>
              {filterSummary}
            </Text>
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 18,
    padding: 14,
    gap: 12,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
  },
  resultCount: {
    fontSize: 14,
    fontWeight: '700',
  },
  resultSubtitle: {
    marginTop: 4,
    fontSize: 12,
    lineHeight: 17,
  },
  clearText: {
    fontSize: 13,
    fontWeight: '700',
  },
  filterRow: {
    gap: 8,
    paddingBottom: 2,
  },
  filterChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    maxWidth: 160,
  },
  filterChipCompact: {
    paddingHorizontal: 11,
    paddingVertical: 7,
  },
  filterChipText: {
    fontSize: 12,
    fontWeight: '700',
  },
  quickActionsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  quickFilterButton: {
    flex: 1,
    minHeight: 42,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  quickFilterText: {
    flex: 1,
    fontSize: 13,
    fontWeight: '600',
  },
  advancedPanel: {
    gap: 12,
    paddingTop: 2,
  },
  advancedSection: {
    gap: 8,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  summaryRow: {
    paddingTop: 2,
  },
  summaryText: {
    fontSize: 12,
    lineHeight: 18,
  },
});
