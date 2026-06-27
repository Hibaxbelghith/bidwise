import { useRef, useEffect } from 'react';
import { ChevronDown, SlidersHorizontal, X, Search } from 'lucide-react';
import { Button } from '../../../components/ui/button.jsx';
import { STATUS_OPTIONS } from '../../opportunities/constants/opportunityOptions.js';
import { TUNISIAN_LOCATION_OPTIONS } from '../../profile/profilePreferences.js';
import { ORGANIZATION_FILTER_TYPE_OPTIONS } from '../hooks/useOpportunitiesFiltering.js';
import { useLanguage } from '../../../i18n/LanguageContext.jsx';
import {
  getOrganizationOpportunityStatusLabel,
  getOrganizationOpportunityTypeLabel,
} from '../utils/organizationLabelUtils.js';

const OpportunitiesFilterBar = ({
  selectedStatuses,
  isStatusDropdownOpen,
  setIsStatusDropdownOpen,
  toggleStatusFilter,
  toggleAllStatuses,
  selectedLocations,
  isLocationDropdownOpen,
  setIsLocationDropdownOpen,
  toggleLocationFilter,
  toggleAllLocations,
  locationSearchTerm,
  setLocationSearchTerm,
  filteredLocationOptions,
  locationCountMap,
  selectedTypes,
  isTypeDropdownOpen,
  setIsTypeDropdownOpen,
  toggleTypeFilter,
  toggleAllTypes,
  totalResults,
  onResetAllFilters,
  onCloseDropdowns,
}) => {
  const { t } = useLanguage();
  const statusDropdownRef = useRef(null);
  const locationDropdownRef = useRef(null);
  const typeDropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (statusDropdownRef.current && !statusDropdownRef.current.contains(event.target)) {
        setIsStatusDropdownOpen(false);
      }
      if (locationDropdownRef.current && !locationDropdownRef.current.contains(event.target)) {
        setIsLocationDropdownOpen(false);
      }
      if (typeDropdownRef.current && !typeDropdownRef.current.contains(event.target)) {
        setIsTypeDropdownOpen(false);
      }
    };

    if (isStatusDropdownOpen || isLocationDropdownOpen || isTypeDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isStatusDropdownOpen, isLocationDropdownOpen, isTypeDropdownOpen, setIsStatusDropdownOpen, setIsLocationDropdownOpen, setIsTypeDropdownOpen]);

  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-neutral-100 px-5 py-4">
      <div className="relative" ref={typeDropdownRef}>
        <Button 
          variant="outline" 
          className="h-10 rounded-xl border-neutral-400 bg-white"
          onClick={() => setIsTypeDropdownOpen(!isTypeDropdownOpen)}
        >
          <span className="font-semibold text-blue-700">({selectedTypes.length})</span>
          {t('organization.type')}
          <ChevronDown className="h-4 w-4" aria-hidden="true" />
        </Button>

        {isTypeDropdownOpen && (
          <div className="absolute top-full left-0 mt-2 w-64 rounded-xl border border-neutral-200 bg-white shadow-lg z-50">
            <div className="border-b border-neutral-100 px-4 py-3">
              <label className="flex items-center gap-3 cursor-pointer hover:bg-neutral-50 px-1 py-1 rounded">
                <input
                  type="checkbox"
                  checked={selectedTypes.length === ORGANIZATION_FILTER_TYPE_OPTIONS.length}
                  onChange={(e) => toggleAllTypes(e.target.checked)}
                  className="w-4 h-4 rounded border-neutral-300"
                />
                <span className="text-sm font-semibold text-neutral-950">{t('organization.selectAll')}</span>
              </label>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {ORGANIZATION_FILTER_TYPE_OPTIONS.map((type) => (
                <label
                  key={type.value}
                  className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-neutral-50 border-b border-neutral-50 last:border-b-0 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedTypes.includes(type.value)}
                    onChange={() => toggleTypeFilter(type.value)}
                    className="w-4 h-4 rounded border-neutral-300"
                  />
                  <span className="text-sm text-neutral-700">
                    {getOrganizationOpportunityTypeLabel(type.value, t, type.label)}
                  </span>
                </label>
              ))}
            </div>
            <div className="border-t border-neutral-100 px-4 py-2 flex justify-between">
              <button
                onClick={() => setIsTypeDropdownOpen(false)}
                className="text-sm text-blue-700 font-semibold hover:text-blue-800"
              >
                {t('organization.done')}
              </button>
              <button
                onClick={() => toggleAllTypes(true)}
                className="text-sm text-neutral-600 hover:text-neutral-700"
              >
                {t('organization.reset')}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="relative" ref={statusDropdownRef}>
        <Button 
          variant="outline" 
          className="h-10 rounded-xl border-neutral-400 bg-white"
          onClick={() => setIsStatusDropdownOpen(!isStatusDropdownOpen)}
        >
          <span className="font-semibold text-blue-700">({selectedStatuses.length})</span>
          {t('organization.status')}
          <ChevronDown className="h-4 w-4" aria-hidden="true" />
        </Button>

        {isStatusDropdownOpen && (
          <div className="absolute top-full left-0 mt-2 w-64 rounded-xl border border-neutral-200 bg-white shadow-lg z-50">
            <div className="border-b border-neutral-100 px-4 py-3">
              <label className="flex items-center gap-3 cursor-pointer hover:bg-neutral-50 px-1 py-1 rounded">
                <input
                  type="checkbox"
                  checked={selectedStatuses.length === STATUS_OPTIONS.length}
                  onChange={(e) => toggleAllStatuses(e.target.checked)}
                  className="w-4 h-4 rounded border-neutral-300"
                />
                <span className="text-sm font-semibold text-neutral-950">{t('organization.selectAll')}</span>
              </label>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {STATUS_OPTIONS.map((status) => (
                <label
                  key={status.value}
                  className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-neutral-50 border-b border-neutral-50 last:border-b-0 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedStatuses.includes(status.value)}
                    onChange={() => toggleStatusFilter(status.value)}
                    className="w-4 h-4 rounded border-neutral-300"
                  />
                  <span className="text-sm text-neutral-700">
                    {getOrganizationOpportunityStatusLabel(status.value, t, status.label)}
                  </span>
                </label>
              ))}
            </div>
            <div className="border-t border-neutral-100 px-4 py-2 flex justify-between">
              <button
                onClick={() => setIsStatusDropdownOpen(false)}
                className="text-sm text-blue-700 font-semibold hover:text-blue-800"
              >
                {t('organization.done')}
              </button>
              <button
                onClick={() => toggleAllStatuses(true)}
                className="text-sm text-neutral-600 hover:text-neutral-700"
              >
                {t('organization.reset')}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="relative" ref={locationDropdownRef}>
        <Button 
          variant="outline" 
          className="h-10 rounded-xl border-neutral-400 bg-white"
          onClick={() => setIsLocationDropdownOpen(!isLocationDropdownOpen)}
        >
          <span className="font-semibold text-blue-700">({selectedLocations.length})</span>
          {t('organization.location')}
          <ChevronDown className="h-4 w-4" aria-hidden="true" />
        </Button>

        {isLocationDropdownOpen && (
          <div className="absolute top-full left-0 mt-2 w-80 rounded-xl border border-neutral-200 bg-white shadow-lg z-50">
            <div className="border-b border-neutral-100 px-4 py-3">
              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-neutral-400" />
                <input
                  type="text"
                  placeholder={t('organization.searchLocations')}
                  value={locationSearchTerm}
                  onChange={(e) => setLocationSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <label className="flex items-center gap-3 cursor-pointer hover:bg-neutral-50 px-1 py-1 rounded">
                <input
                  type="checkbox"
                  checked={selectedLocations.length === TUNISIAN_LOCATION_OPTIONS.length}
                  onChange={(e) => toggleAllLocations(e.target.checked)}
                  className="w-4 h-4 rounded border-neutral-300"
                />
                <span className="text-sm font-semibold text-neutral-950">{t('organization.selectAll')}</span>
              </label>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {filteredLocationOptions.length > 0 ? (
                filteredLocationOptions.map((location) => (
                  <label
                    key={location}
                    className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-neutral-50 border-b border-neutral-50 last:border-b-0 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedLocations.includes(location)}
                      onChange={() => toggleLocationFilter(location)}
                      className="w-4 h-4 rounded border-neutral-300"
                    />
                    <span className="text-sm text-neutral-700 flex-1">{location}</span>
                    <span className="text-xs text-neutral-500 font-medium">({locationCountMap[location] || 0})</span>
                  </label>
                ))
              ) : (
                <div className="px-4 py-6 text-center text-sm text-neutral-500">
                  {t('organization.noLocationsFound')}
                </div>
              )}
            </div>
            <div className="border-t border-neutral-100 px-4 py-2 flex justify-between">
              <button
                onClick={() => setIsLocationDropdownOpen(false)}
                className="text-sm text-blue-700 font-semibold hover:text-blue-800"
              >
                {t('organization.done')}
              </button>
              <button
                onClick={() => {
                  toggleAllLocations(true);
                  setLocationSearchTerm('');
                }}
                className="text-sm text-neutral-600 hover:text-neutral-700"
              >
                {t('organization.reset')}
              </button>
            </div>
          </div>
        )}
      </div>

      <Button variant="outline" className="h-10 rounded-xl border-neutral-400 bg-white">
        <SlidersHorizontal className="h-4 w-4 text-blue-700" aria-hidden="true" />
        {selectedStatuses.length > 0 || selectedLocations.length > 0 || selectedTypes.length > 0 ? (
          <span className="font-semibold text-blue-700">
            {t('organization.filtersApplied', { count: selectedStatuses.length + selectedLocations.length + selectedTypes.length })}
          </span>
        ) : (
          t('organization.noFilters')
        )}
      </Button>
      <span className="text-sm font-semibold text-neutral-600">
        {totalResults === null ? t('auth.loading') : t('organization.resultsCount', { count: totalResults })}
      </span>
    </div>
  );
};

export default OpportunitiesFilterBar;
