import { useState, useCallback, useMemo } from 'react';
import { STATUS_OPTIONS, TYPE_OPTIONS } from '../../opportunities/constants/opportunityOptions.js';
import { TUNISIAN_LOCATION_OPTIONS } from '../../profile/profilePreferences.js';

export const useOpportunitiesFiltering = () => {
  const [selectedStatuses, setSelectedStatuses] = useState(STATUS_OPTIONS.map(s => s.value));
  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false);
  const [selectedLocations, setSelectedLocations] = useState(TUNISIAN_LOCATION_OPTIONS);
  const [isLocationDropdownOpen, setIsLocationDropdownOpen] = useState(false);
  const [locationSearchTerm, setLocationSearchTerm] = useState('');
  const [selectedTypes, setSelectedTypes] = useState(TYPE_OPTIONS.map(t => t.value));
  const [isTypeDropdownOpen, setIsTypeDropdownOpen] = useState(false);

  const toggleStatusFilter = useCallback((statusValue) => {
    setSelectedStatuses((current) => {
      if (current.includes(statusValue)) {
        return current.filter(s => s !== statusValue);
      }
      return [...current, statusValue];
    });
  }, []);

  const toggleAllStatuses = useCallback((checked) => {
    if (checked) {
      setSelectedStatuses(STATUS_OPTIONS.map(s => s.value));
    } else {
      setSelectedStatuses([]);
    }
  }, []);

  const toggleLocationFilter = useCallback((location) => {
    setSelectedLocations((current) => {
      if (current.includes(location)) {
        return current.filter(l => l !== location);
      }
      return [...current, location];
    });
  }, []);

  const toggleAllLocations = useCallback((checked) => {
    if (checked) {
      setSelectedLocations(TUNISIAN_LOCATION_OPTIONS);
    } else {
      setSelectedLocations([]);
    }
  }, []);

  const toggleTypeFilter = useCallback((typeValue) => {
    setSelectedTypes((current) => {
      if (current.includes(typeValue)) {
        return current.filter(t => t !== typeValue);
      }
      return [...current, typeValue];
    });
  }, []);

  const toggleAllTypes = useCallback((checked) => {
    if (checked) {
      setSelectedTypes(TYPE_OPTIONS.map(t => t.value));
    } else {
      setSelectedTypes([]);
    }
  }, []);

  const locationCountMap = useMemo(() => {
    return {}; // Sera calculé après avec les opportunities
  }, []);

  const filteredLocationOptions = useMemo(() => {
    const searchLower = locationSearchTerm.toLowerCase();
    return TUNISIAN_LOCATION_OPTIONS.filter(location =>
      location.toLowerCase().includes(searchLower)
    );
  }, [locationSearchTerm]);

  const resetAllFilters = useCallback(() => {
    setSelectedStatuses(STATUS_OPTIONS.map(s => s.value));
    setSelectedLocations(TUNISIAN_LOCATION_OPTIONS);
    setSelectedTypes(TYPE_OPTIONS.map(t => t.value));
    setLocationSearchTerm('');
  }, []);

  return {
    // States
    selectedStatuses,
    isStatusDropdownOpen,
    setIsStatusDropdownOpen,
    selectedLocations,
    isLocationDropdownOpen,
    setIsLocationDropdownOpen,
    locationSearchTerm,
    setLocationSearchTerm,
    selectedTypes,
    isTypeDropdownOpen,
    setIsTypeDropdownOpen,
    // Toggles
    toggleStatusFilter,
    toggleAllStatuses,
    toggleLocationFilter,
    toggleAllLocations,
    toggleTypeFilter,
    toggleAllTypes,
    // Computed
    filteredLocationOptions,
    // Actions
    resetAllFilters,
  };
};
