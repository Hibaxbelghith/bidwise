import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import {
  ChevronDown,
  FilePlus2,
  MessageSquare,
  SlidersHorizontal,
  Star,
} from 'lucide-react';

import { Badge } from '../../../components/ui/badge.jsx';
import { Button } from '../../../components/ui/button.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../../components/ui/table.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import { listOrganizationOpportunities } from '../services/organizationService.js';

const TYPE_LABELS = {
  EMPLOI: 'Job',
  STAGE: 'Internship',
  PROJET: 'Call for tender',
  SAISONNIER: 'Seasonal job',
};

const STATUS_LABELS = {
  ACTIVE: 'Active',
  PENDING_REVIEW: 'Pending',
  REJECTED: 'Rejected',
  INACTIVE: 'Inactive',
  EXPIRED: 'Expired',
  EXPIREE: 'Expired',
  ARCHIVED: 'Archived',
  ARCHIVEE: 'Archived',
};

const STATUS_VARIANTS = {
  ACTIVE: 'default',
  PENDING_REVIEW: 'outline',
  REJECTED: 'destructive',
  INACTIVE: 'secondary',
  EXPIRED: 'secondary',
  EXPIREE: 'secondary',
  ARCHIVED: 'secondary',
  ARCHIVEE: 'secondary',
};

const OpportunityStatusBadge = ({ status }) => {
  const label = STATUS_LABELS[status] || status || 'Pending';
  const badge = (
    <Badge variant={STATUS_VARIANTS[status] || 'outline'}>
      {label}
    </Badge>
  );

  if (status !== 'PENDING_REVIEW') {
    return badge;
  }

  return (
    <span className="group relative inline-flex">
      <span className="cursor-help border-b border-blue-600 pb-0.5">
        {badge}
      </span>
      <span className="pointer-events-none absolute left-0 top-full z-20 mt-2 hidden w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-left text-xs font-medium leading-5 text-neutral-700 shadow-lg group-hover:block">
        Your opportunity is being reviewed before publication.
      </span>
    </span>
  );
};

const formatDate = (value) => {
  if (!value) return 'Not set';
  try {
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(value));
  } catch {
    return value;
  }
};

const OrganizationDashboardPage = () => {
  const { loading, user } = useAuth();
  const profile = user?.organization_profile;
  const [opportunities, setOpportunities] = useState([]);
  const [isLoadingOpportunities, setIsLoadingOpportunities] = useState(true);
  const [opportunitiesError, setOpportunitiesError] = useState('');

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

                <div className="overflow-hidden rounded-lg border border-neutral-200">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-neutral-50">
                        <TableHead>Title</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Location</TableHead>
                        <TableHead>Published</TableHead>
                        <TableHead className="text-right">Applications</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {opportunities.map((opportunity) => (
                        <TableRow key={opportunity.id}>
                          <TableCell className="font-medium text-neutral-950">{opportunity.title}</TableCell>
                          <TableCell>
                            <Badge variant="secondary">{TYPE_LABELS[opportunity.type] || opportunity.type}</Badge>
                          </TableCell>
                          <TableCell>
                            <OpportunityStatusBadge status={opportunity.status} />
                          </TableCell>
                          <TableCell className="text-neutral-600">{opportunity.location || 'Not set'}</TableCell>
                          <TableCell className="text-neutral-600">{formatDate(opportunity.published_at)}</TableCell>
                          <TableCell className="text-right font-medium">{opportunity.applications_count || 0}</TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button variant="ghost" size="sm">
                                Edit
                              </Button>
                              {opportunity.status === 'PENDING_REVIEW' ? (
                                <Button variant="ghost" size="sm" disabled>
                                  Under review
                                </Button>
                              ) : (
                                <Button variant="ghost" size="sm" asChild>
                                  <Link to={`/opportunities/${opportunity.id}`}>View</Link>
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
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
    </section>
  );
};

export default OrganizationDashboardPage;
