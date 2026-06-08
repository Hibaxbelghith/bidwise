import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import {
  ChevronDown,
  FilePlus2,
  MessageSquare,
  SlidersHorizontal,
  Star,
} from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import OrganizationOpportunitiesTable from '../components/OrganizationOpportunitiesTable.jsx';
import {
  OrganizationOpportunityStatusDialog,
  statusFallbackForAction,
} from '../components/OrganizationOpportunityStatus.jsx';
import { listOrganizationOpportunities } from '../services/organizationService.js';
import { changeOrganizationOpportunityStatus } from '../services/organizationService.js';

const OrganizationDashboardPage = () => {
  const { loading, user } = useAuth();
  const profile = user?.organization_profile;
  const [opportunities, setOpportunities] = useState([]);
  const [isLoadingOpportunities, setIsLoadingOpportunities] = useState(true);
  const [opportunitiesError, setOpportunitiesError] = useState('');
  const [pendingStatusAction, setPendingStatusAction] = useState(null);
  const [statusActionId, setStatusActionId] = useState(null);

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

  const stats = useMemo(() => {
    const active = opportunities.filter((item) => item.status === 'ACTIVE').length;
    const applications = opportunities.reduce(
      (total, item) => total + Number(item.applications_count || 0),
      0
    );
    return {
      active,
      applications,
      total: opportunities.length,
    };
  }, [opportunities]);

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
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[286px_1fr]">
        <OrganizationSidebar activePath="/organization/dashboard" />

        <div className="min-w-0">
          <div className="border-b border-neutral-200 bg-[#efeeec] px-5 py-4">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex flex-wrap items-center gap-5">
                <h1 id="organization-dashboard-heading" className="text-2xl font-semibold text-neutral-950">
                  Jobs
                </h1>
                <div className="hidden h-8 w-px bg-neutral-300 sm:block" />
                <div className="flex rounded-2xl bg-transparent p-0">
                  <button type="button" className="rounded-2xl bg-neutral-700 px-5 py-3 text-sm font-semibold text-white">
                    All jobs
                  </button>
                  <button type="button" className="rounded-2xl px-5 py-3 text-sm font-medium text-neutral-700 hover:bg-white/70">
                    Tags
                  </button>
                </div>
              </div>

              <Button asChild className="h-12 rounded-xl bg-blue-700 px-5 text-white hover:bg-blue-800">
                <Link to="/organization/post">
                  <FilePlus2 className="h-4 w-4" aria-hidden="true" />
                  Publish an opportunity
                </Link>
              </Button>
            </div>
          </div>

          <div className="rounded-tl-xl bg-white">
            <div className="flex flex-wrap items-center gap-3 border-b border-neutral-100 px-5 py-4">
              <Button variant="outline" className="h-10 rounded-xl border-neutral-400 bg-white">
                <span className="font-semibold text-blue-700">(2)</span>
                Status
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button variant="outline" className="h-10 rounded-xl border-neutral-400 bg-white">
                Title
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button variant="outline" className="h-10 rounded-xl border-neutral-400 bg-white">
                Location
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button variant="outline" size="icon" className="h-10 w-14 rounded-xl border-neutral-400 bg-white">
                <Star className="h-5 w-5" aria-hidden="true" />
              </Button>
              <Button variant="outline" className="h-10 rounded-xl border-neutral-400 bg-white">
                <SlidersHorizontal className="h-4 w-4 text-blue-700" aria-hidden="true" />
                1 filter applied
              </Button>
              <span className="text-sm font-semibold text-neutral-600">
                {isLoadingOpportunities ? 'Loading' : `${opportunities.length} result${opportunities.length === 1 ? '' : 's'}`}
              </span>
            </div>

            {opportunitiesError ? (
              <div className="mx-5 mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {opportunitiesError}
              </div>
            ) : null}

            {isLoadingOpportunities ? (
              <div className="flex min-h-[560px] flex-col items-center justify-center px-6 py-12 text-center">
                <div className="flex items-center gap-3 rounded-xl border border-neutral-200 bg-white px-5 py-4 text-sm font-semibold text-neutral-600 shadow-sm">
                  <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue-700" />
                  Loading your published opportunities
                </div>
              </div>
            ) : opportunities.length > 0 ? (
              <div className="px-5 py-5">
                <div className="mb-4 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border border-neutral-200 bg-white p-4">
                    <p className="text-sm text-neutral-500">Published jobs</p>
                    <p className="mt-1 text-2xl font-semibold text-neutral-950">{stats.total}</p>
                  </div>
                  <div className="rounded-lg border border-neutral-200 bg-white p-4">
                    <p className="text-sm text-neutral-500">Active jobs</p>
                    <p className="mt-1 text-2xl font-semibold text-neutral-950">{stats.active}</p>
                  </div>
                  <div className="rounded-lg border border-neutral-200 bg-white p-4">
                    <p className="text-sm text-neutral-500">Applications</p>
                    <p className="mt-1 text-2xl font-semibold text-neutral-950">{stats.applications}</p>
                  </div>
                </div>

                <OrganizationOpportunitiesTable
                  opportunities={opportunities}
                  statusActionId={statusActionId}
                  onStatusAction={handleStatusAction}
                />
              </div>
            ) : (
              <div className="flex min-h-[560px] flex-col items-center justify-center px-6 py-12 text-center">
                <div className="mb-8 flex h-44 w-72 items-center justify-center rounded-[2rem] bg-[#f6d0a5]">
                  <div className="relative h-28 w-44">
                    <div className="absolute bottom-0 left-4 h-16 w-32 rounded-t-[4rem] bg-[#eaa24d]" />
                    <div className="absolute left-12 top-2 h-16 w-16 rounded-full bg-[#2d2d2d]" />
                    <div className="absolute left-24 top-14 h-14 w-24 rounded-xl bg-white shadow-sm" />
                    <div className="absolute right-0 top-0 h-16 w-16 rounded-full bg-[#79b7a3]" />
                    <div className="absolute right-5 top-5 h-12 w-8 rounded-t-full bg-[#4a987d]" />
                  </div>
                </div>
                <h2 className="max-w-4xl text-2xl font-semibold text-neutral-950">
                  Publish your first opportunity and start receiving qualified applications.
                </h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">
                  Create a job, internship, seasonal role, or call for tender directly on BidWise. Your organization
                  will be able to manage opportunities and track applications from this workspace.
                </p>
                <Button asChild className="mt-8 h-12 rounded-xl bg-blue-700 px-5 text-white hover:bg-blue-800">
                  <Link to="/organization/post">
                    <FilePlus2 className="h-4 w-4" aria-hidden="true" />
                    Publish an opportunity
                  </Link>
                </Button>
              </div>
            )}
          </div>

          <div className="fixed bottom-5 right-5 hidden rounded-full bg-blue-700 p-4 text-white shadow-xl shadow-blue-950/20 lg:block">
            <MessageSquare className="h-5 w-5" aria-hidden="true" />
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
