// AdminUsersFilters.jsx
import { memo, useState } from 'react';
import { Filter, Search, X, ChevronDown, ChevronUp, Calendar, Shield, Activity } from 'lucide-react';
import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import { Label } from '../../../components/ui/label.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../../components/ui/select.jsx';

const AdminUsersFilters = ({
  searchDraft,
  onSearchDraftChange,
  role,
  status,
  joinedAfter,
  joinedBefore,
  lastLoginAfter,
  lastLoginBefore,
  activeAdvancedFilters,
  onUpdateQueryParams,
  onResetFilters,
}) => {
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);

  const hasBaseFilters = (searchDraft !== '') || (role !== '') || (status !== '');
  const hasActiveFilters = hasBaseFilters || activeAdvancedFilters > 0;

  const handleSearchChange = (value) => {
    onSearchDraftChange(value);
  };

  const handleRoleChange = (value) => {
    onUpdateQueryParams({ role: value === 'all' ? '' : value, page: '1' });
  };

  const handleStatusChange = (value) => {
    onUpdateQueryParams({ status: value === 'all' ? '' : value, page: '1' });
  };

  const handleClearAll = () => {
    onResetFilters();
    setIsAdvancedOpen(false);
  };

  const clearSearch = () => {
    onSearchDraftChange('');
    onUpdateQueryParams({ search: '', page: '1' });
  };

  const clearRole = () => {
    onUpdateQueryParams({ role: '', page: '1' });
  };

  const clearStatus = () => {
    onUpdateQueryParams({ status: '', page: '1' });
  };

  const getRoleLabel = (val) => {
    if (val === 'admin') return 'Admin';
    if (val === 'user') return 'User';
    return val;
  };

  const getStatusLabel = (val) => {
    if (val === 'active') return 'Active';
    if (val === 'suspended') return 'Suspended';
    return val;
  };

  return (
    <div className="space-y-4">
      {/* Barre de recherche principale */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Champ de recherche */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <Input
            type="text"
            placeholder="Search by email or name..."
            value={searchDraft}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="h-10 pl-19 pr-9 border-neutral-200 bg-white text-sm placeholder:text-neutral-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          {searchDraft && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 transition-colors hover:text-neutral-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
            className={`h-10 gap-2 border-neutral-200 transition-all ${
              isAdvancedOpen 
                ? 'bg-blue-50 border-blue-200 text-blue-700' 
                : 'text-neutral-600 hover:bg-neutral-50'
            }`}
          >
            <Filter className="h-4 w-4" />
            <span>Filters</span>
            {hasActiveFilters && (
              <span className="ml-1 flex h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
            )}
            {isAdvancedOpen ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
          
          {hasActiveFilters && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleClearAll}
              className="h-10 text-neutral-500 hover:text-neutral-700"
            >
              Clear all
            </Button>
          )}
        </div>
      </div>

      {/* Panneau des filtres avancés */}
      {isAdvancedOpen && (
        <div className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm transition-all">
          {/* Grille des filtres */}
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {/* Filtre Role */}
            <div className="space-y-1.5">
              <Label className="flex items-center gap-1.5 text-xs font-medium text-neutral-500">
                <Shield className="h-3.5 w-3.5" />
                Role
              </Label>
              <Select 
                value={role || 'all'} 
                onValueChange={handleRoleChange}
              >
                <SelectTrigger className="h-9 border-neutral-200 bg-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
                  <SelectValue placeholder="All roles" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All roles</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="candidate">Candidat</SelectItem>
                  <SelectItem value="organization">Promoteur</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Filtre Status */}
            <div className="space-y-1.5">
              <Label className="flex items-center gap-1.5 text-xs font-medium text-neutral-500">
                <Activity className="h-3.5 w-3.5" />
                Status
              </Label>
              <Select 
                value={status || 'all'} 
                onValueChange={handleStatusChange}
              >
                <SelectTrigger className="h-9 border-neutral-200 bg-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Filtre Date - Joined */}
            <div className="space-y-1.5">
              <Label className="flex items-center gap-1.5 text-xs font-medium text-neutral-500">
                <Calendar className="h-3.5 w-3.5" />
                Joined after
              </Label>
              <Input
                type="date"
                value={joinedAfter || ''}
                onChange={(e) => onUpdateQueryParams({ joined_after: e.target.value, page: '1' })}
                className="h-9 border-neutral-200 bg-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Deuxième ligne pour les dates supplémentaires */}
          <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-neutral-500">Joined before</Label>
              <Input
                type="date"
                value={joinedBefore || ''}
                onChange={(e) => onUpdateQueryParams({ joined_before: e.target.value, page: '1' })}
                className="h-9 border-neutral-200 bg-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-neutral-500">Last login after</Label>
              <Input
                type="date"
                value={lastLoginAfter || ''}
                onChange={(e) => onUpdateQueryParams({ last_login_after: e.target.value, page: '1' })}
                className="h-9 border-neutral-200 bg-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-neutral-500">Last login before</Label>
              <Input
                type="date"
                value={lastLoginBefore || ''}
                onChange={(e) => onUpdateQueryParams({ last_login_before: e.target.value, page: '1' })}
                className="h-9 border-neutral-200 bg-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Badges des filtres actifs */}
          {hasActiveFilters && (
            <div className="mt-5 flex flex-wrap items-center gap-2 pt-4 border-t border-neutral-100">
              <span className="text-xs font-medium text-neutral-400">Active filters:</span>
              
              {role && role !== '' && (
                <FilterBadge 
                  label={`Role: ${getRoleLabel(role)}`} 
                  onClear={clearRole} 
                />
              )}
              
              {status && status !== '' && (
                <FilterBadge 
                  label={`Status: ${getStatusLabel(status)}`} 
                  onClear={clearStatus} 
                />
              )}
              
              {searchDraft && (
                <FilterBadge 
                  label={`Search: ${searchDraft.length > 25 ? searchDraft.slice(0, 25) + '...' : searchDraft}`} 
                  onClear={clearSearch} 
                />
              )}
              
              {joinedAfter && (
                <FilterBadge 
                  label={`Joined after: ${joinedAfter}`} 
                  onClear={() => onUpdateQueryParams({ joined_after: '', page: '1' })} 
                />
              )}
              
              {joinedBefore && (
                <FilterBadge 
                  label={`Joined before: ${joinedBefore}`} 
                  onClear={() => onUpdateQueryParams({ joined_before: '', page: '1' })} 
                />
              )}
              
              {lastLoginAfter && (
                <FilterBadge 
                  label={`Login after: ${lastLoginAfter}`} 
                  onClear={() => onUpdateQueryParams({ last_login_after: '', page: '1' })} 
                />
              )}
              
              {lastLoginBefore && (
                <FilterBadge 
                  label={`Login before: ${lastLoginBefore}`} 
                  onClear={() => onUpdateQueryParams({ last_login_before: '', page: '1' })} 
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Composant pour les badges de filtres actifs
const FilterBadge = ({ label, onClear }) => (
  <span className="inline-flex items-center gap-1.5 rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700 transition-all hover:bg-neutral-200">
    {label}
    <button 
      onClick={onClear} 
      className="ml-0.5 rounded-full p-0.5 transition-colors hover:bg-neutral-300"
    >
      <X className="h-2.5 w-2.5" />
    </button>
  </span>
);

export default memo(AdminUsersFilters);