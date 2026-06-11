import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { FilePlus2 } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import {
  OrganizationOpportunityStatusDialog,
  statusFallbackForAction,
} from '../components/OrganizationOpportunityStatus.jsx';
import { listOrganizationOpportunities } from '../services/organizationService.js';
import { changeOrganizationOpportunityStatus } from '../services/organizationService.js';
import { useOpportunitiesFiltering } from '../hooks/useOpportunitiesFiltering.js';
import OpportunitiesFilterBar from '../components/OpportunitiesFilterBar.jsx';
import OpportunitiesContent from '../components/OpportunitiesContent.jsx';
import { STATUS_OPTIONS, TYPE_OPTIONS } from '../../opportunities/constants/opportunityOptions.js';
import { TUNISIAN_LOCATION_OPTIONS } from '../../profile/profilePreferences.js';

const OrganizationDashboardPage = () => {
  const { loading, user } = useAuth();
  const profile = user?.organization_profile;
  const [opportunities, setOpportunities] = useState([]);
  const [isLoadingOpportunities, setIsLoadingOpportunities] = useState(true);
  const [opportunitiesError, setOpportunitiesError] = useState('');
  const [pendingStatusAction, setPendingStatusAction] = useState(null);
  const [statusActionId, setStatusActionId] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const filters = useOpportunitiesFiltering();

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, []);

  useEffect(() => {
    let isCancelled = false;

    if (!isOrganizationProfileComplete(profile)) {
      setOpportunities([]);
      return undefined;
    }

    const fetchOpportunities = async () => {
      try {
        setIsLoadingOpportunities(true);
        setOpportunitiesError('');
        const data = await listOrganizationOpportunities();
        if (!isCancelled) {
          setOpportunities(data);
        }
      } catch (error) {
        if (!isCancelled) {
          setOpportunities([]);
          setOpportunitiesError(
            error?.response?.data?.detail || 'Unable to load your published opportunities.'
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingOpportunities(false);
        }
      }
    };

    fetchOpportunities();

    return () => {
      isCancelled = true;
    };
  }, [profile]);

  const filteredOpportunities = useMemo(() => {
    return opportunities.filter(opp => 
      filters.selectedStatuses.includes(opp.status) &&
      filters.selectedLocations.includes(opp.location) &&
      filters.selectedTypes.includes(opp.type)
    );
  }, [opportunities, filters.selectedStatuses, filters.selectedLocations, filters.selectedTypes]);

  const stats = useMemo(() => {
    const active = filteredOpportunities.filter((item) => item.status === 'ACTIVE').length;
    const applications = filteredOpportunities.reduce(
      (total, item) => total + Number(item.applications_count || 0),
      0
    );
    return {
      active,
      applications,
      total: filteredOpportunities.length,
    };
  }, [filteredOpportunities]);

  const locationCountMap = useMemo(() => {
    const map = {};
    opportunities.forEach(opp => {
      if (filters.selectedStatuses.includes(opp.status) && filters.selectedTypes.includes(opp.type) && filters.selectedLocations.includes(opp.location)) {
        map[opp.location] = (map[opp.location] || 0) + 1;
      }
    });
    return map;
  }, [opportunities, filters.selectedStatuses, filters.selectedTypes, filters.selectedLocations]);

  const applyStatusAction = async (opportunity, action) => {
    try {
      setStatusActionId(opportunity.id);
      setOpportunitiesError('');
      const result = await changeOrganizationOpportunityStatus(opportunity.id, action);
      const serverOpportunity = result?.opportunity;
      const nextStatus = serverOpportunity?.status || statusFallbackForAction(opportunity, action);
      setOpportunities((current) => current.map((item) => (
        item.id === opportunity.id
          ? {
              ...item,
              ...(serverOpportunity || {}),
              status: nextStatus,
            }
          : item
      )));
      setPendingStatusAction(null);
    } catch (error) {
      setOpportunitiesError(error?.response?.data?.detail || 'Unable to update opportunity status.');
    } finally {
      setStatusActionId(null);
    }
  };

  const handleStatusAction = (opportunity, action) => {
    if (action === 'activate') {
      applyStatusAction(opportunity, action);
      return;
    }
    setPendingStatusAction({ opportunity, action });
  };

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-neutral-50 px-4">
        <div className="rounded-lg border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-600">
          Loading organization workspace
        </div>
      </section>
    );
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-[#f4f3f1]" aria-labelledby="organization-dashboard-heading">
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[auto_1fr]">
        <OrganizationSidebar activePath="/organization/dashboard" isCollapsed={isSidebarCollapsed} onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)} />

        <div className="min-w-0">
          <div className="border-b border-neutral-200 bg-[#efeeec] px-5 py-4">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <Button asChild className="h-12 rounded-xl bg-blue-700 px-5 text-white hover:bg-blue-800 ml-auto">
                <Link to="/organization/post">
                  <FilePlus2 className="h-4 w-4" aria-hidden="true" />
                  Publish an opportunity
                </Link>
              </Button>
            </div>
          </div>

          <div className="rounded-tl-xl bg-white">
            <OpportunitiesFilterBar
              selectedStatuses={filters.selectedStatuses}
              isStatusDropdownOpen={filters.isStatusDropdownOpen}
              setIsStatusDropdownOpen={filters.setIsStatusDropdownOpen}
              toggleStatusFilter={filters.toggleStatusFilter}
              toggleAllStatuses={filters.toggleAllStatuses}
              selectedLocations={filters.selectedLocations}
              isLocationDropdownOpen={filters.isLocationDropdownOpen}
              setIsLocationDropdownOpen={filters.setIsLocationDropdownOpen}
              toggleLocationFilter={filters.toggleLocationFilter}
              toggleAllLocations={filters.toggleAllLocations}
              locationSearchTerm={filters.locationSearchTerm}
              setLocationSearchTerm={filters.setLocationSearchTerm}
              filteredLocationOptions={filters.filteredLocationOptions}
              locationCountMap={locationCountMap}
              selectedTypes={filters.selectedTypes}
              isTypeDropdownOpen={filters.isTypeDropdownOpen}
              setIsTypeDropdownOpen={filters.setIsTypeDropdownOpen}
              toggleTypeFilter={filters.toggleTypeFilter}
              toggleAllTypes={filters.toggleAllTypes}
              totalResults={isLoadingOpportunities ? null : filteredOpportunities.length}
              onResetAllFilters={filters.resetAllFilters}
            />

            {opportunitiesError ? (
              <div className="mx-5 mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {opportunitiesError}
              </div>
            ) : null}

            <OpportunitiesContent
              isLoading={isLoadingOpportunities}
              filteredOpportunities={filteredOpportunities}
              opportunities={opportunities}
              stats={stats}
              statusActionId={statusActionId}
              onStatusAction={handleStatusAction}
              onResetFilters={filters.resetAllFilters}
            />
          </div>

        </div>
      </div>

      <OrganizationOpportunityStatusDialog
        pendingAction={pendingStatusAction}
        onCancel={() => setPendingStatusAction(null)}
        onConfirm={() => applyStatusAction(
          pendingStatusAction.opportunity,
          pendingStatusAction.action,
        )}
        isSubmitting={Boolean(statusActionId)}
      />
    </section>
  );
};

export default OrganizationDashboardPage;
