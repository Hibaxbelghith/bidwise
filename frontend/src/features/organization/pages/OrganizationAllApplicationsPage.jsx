import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { Search, ChevronDown } from 'lucide-react';

import { Spinner } from '../../../components/ui/spinner.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import OrganizationApplicationsTable from '../components/OrganizationApplicationsTable.jsx';
import { listAllOrganizationApplications } from '../services/organizationService.js';
import { getApplicationStatusLabel } from '../../applications/applicationStatusUi.js';

const OrganizationAllApplicationsPage = () => {
  const { loading, user } = useAuth();
  const profile = user?.organization_profile;
  const [searchParams] = useSearchParams();

  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  
  // Search & Filters
  const [searchTerm, setSearchTerm] = useState('');
  const filterParam = searchParams.get('filter');
  const initialStatuses = filterParam === 'new' 
    ? ['SUBMITTED']
    : ['SUBMITTED', 'VIEWED_BY_ORGANIZATION', 'SHORTLISTED', 'REJECTED', 'WITHDRAWN'];
  const [selectedStatuses, setSelectedStatuses] = useState(initialStatuses);
  const [sortBy, setSortBy] = useState('newest');
  const [isSortDropdownOpen, setIsSortDropdownOpen] = useState(false);

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest('[data-dropdown]')) {
        setIsSortDropdownOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  // Update selectedStatuses when filter param changes
  useEffect(() => {
    if (filterParam === 'new') {
      setSelectedStatuses(['SUBMITTED']);
    } else {
      setSelectedStatuses(['SUBMITTED', 'VIEWED_BY_ORGANIZATION', 'SHORTLISTED', 'REJECTED', 'WITHDRAWN']);
    }
  }, [filterParam]);

  useEffect(() => {
    let isCancelled = false;

    if (!isOrganizationProfileComplete(profile)) {
      return undefined;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError('');

        const appData = await listAllOrganizationApplications();
        if (!isCancelled) {
          setApplications(appData);
        }
      } catch (err) {
        if (!isCancelled) {
          setError('Failed to load applications. Please try again.');
          console.error('Error fetching applications:', err);
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchData();
    return () => {
      isCancelled = true;
    };
  }, [profile]);



  // Filter and search applications
  const filteredApplications = useMemo(() => {
    let filtered = applications.filter(app => {
      // Filter by status
      if (!selectedStatuses.includes(app.statut)) return false;

      // Search by: name, email, phone, opportunity title
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matchesName = app.candidate_name.toLowerCase().includes(term);
        const matchesEmail = app.candidate_email.toLowerCase().includes(term);
        const matchesPhone = app.contact_phone.toLowerCase().includes(term);
        const matchesOpportunity = app.opportunity_title.toLowerCase().includes(term);
        
        return matchesName || matchesEmail || matchesPhone || matchesOpportunity;
      }

      return true;
    });

    // Apply sorting
    if (sortBy === 'newest') {
      filtered.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
    } else if (sortBy === 'oldest') {
      filtered.sort((a, b) => new Date(a.submitted_at) - new Date(b.submitted_at));
    } else if (sortBy === 'name-asc') {
      filtered.sort((a, b) => a.candidate_name.localeCompare(b.candidate_name));
    } else if (sortBy === 'opportunity-asc') {
      filtered.sort((a, b) => a.opportunity_title.localeCompare(b.opportunity_title));
    }

    return filtered;
  }, [applications, searchTerm, selectedStatuses, sortBy]);

  // Count applications by status
  const counts = useMemo(() => {
    const statuses = {
      all: applications.length,
      new: applications.filter(app => app.statut === 'SUBMITTED').length,
      viewed: applications.filter(app => app.statut === 'VIEWED_BY_ORGANIZATION').length,
      shortlisted: applications.filter(app => app.statut === 'SHORTLISTED').length,
      rejected: applications.filter(app => app.statut === 'REJECTED').length,
      withdrawn: applications.filter(app => app.statut === 'WITHDRAWN').length,
    };
    return statuses;
  }, [applications]);

  const updateApplicationStatus = (applicationId, nextStatus) => {
    setApplications(prev =>
      nextStatus === '__DELETE__'
        ? prev.filter(app => app.id !== applicationId)
        : prev.map(app => {
            if (app.id !== applicationId) {
              return app;
            }

            const isNormalStatus =
              app.statut === 'SUBMITTED' || app.statut === 'VIEWED_BY_ORGANIZATION';
            const existingRestoreStatus = app._restore_status || null;
            const nextRestoreStatus =
              nextStatus === 'SHORTLISTED' || nextStatus === 'REJECTED'
                ? existingRestoreStatus || (isNormalStatus ? app.statut : null)
                : null;

            return {
              ...app,
              statut: nextStatus,
              derniere_mise_a_jour: new Date().toISOString(),
              _restore_status: nextRestoreStatus,
            };
          })
    );
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
    <section className="min-h-[calc(100vh-4rem)] bg-[#f4f3f1]" aria-labelledby="applications-heading">
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[auto_1fr]">
        <OrganizationSidebar activePath="/organization/applications" isCollapsed={isSidebarCollapsed} onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)} />

        <div className="min-w-0">
          {/* Header */}
          <div className="border-b border-neutral-200 bg-[#efeeec] px-5 py-4">
            <h1 id="applications-heading" className="text-2xl font-semibold text-neutral-900">
              {filterParam === 'new' ? 'New Applications' : 'Applications'}
            </h1>
          </div>

          <div className="rounded-tl-xl bg-white">
            {error ? (
              <div className="mx-5 mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            ) : null}

            {isLoading ? (
              <div className="flex min-h-[560px] flex-col items-center justify-center px-6 py-12">
                <Spinner />
              </div>
            ) : applications.length === 0 ? (
              <div className="flex min-h-[560px] flex-col items-center justify-center px-6 py-12 text-center">
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-6">
                  <p className="text-sm text-neutral-600">
                    No applications yet.
                  </p>
                </div>
              </div>
            ) : (
              <div className="px-5 py-5">
                {/* Search Bar */}
                <div className="mb-6">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-400" />
                    <input
                      type="text"
                      placeholder="Search by candidate name, email, phone, or opportunity title..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-neutral-200 bg-white text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>

                {/* Filters and Sort */}
                <div className="flex flex-wrap gap-3 pb-6 border-b border-neutral-200 mb-6 items-center">
                  {/* Status Filter - Direct Display */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {[
                      { key: 'SUBMITTED', label: getApplicationStatusLabel('SUBMITTED', 'organization'), count: counts.new },
                      { key: 'VIEWED_BY_ORGANIZATION', label: getApplicationStatusLabel('VIEWED_BY_ORGANIZATION', 'organization'), count: counts.viewed },
                      { key: 'SHORTLISTED', label: getApplicationStatusLabel('SHORTLISTED', 'organization'), count: counts.shortlisted },
                      { key: 'REJECTED', label: getApplicationStatusLabel('REJECTED', 'organization'), count: counts.rejected },
                      { key: 'WITHDRAWN', label: getApplicationStatusLabel('WITHDRAWN', 'organization'), count: counts.withdrawn },
                    ].map((status) => (
                      <button
                        key={status.key}
                        onClick={() => {
                          if (selectedStatuses.includes(status.key)) {
                            setSelectedStatuses(selectedStatuses.filter(s => s !== status.key));
                          } else {
                            setSelectedStatuses([...selectedStatuses, status.key]);
                          }
                        }}
                        className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                          selectedStatuses.includes(status.key)
                            ? 'bg-blue-50 border-blue-300 text-blue-700'
                            : 'bg-white border-neutral-200 text-neutral-700 hover:bg-neutral-50'
                        }`}
                      >
                        {status.label} ({status.count})
                      </button>
                    ))}
                  </div>

                  {/* Sort Dropdown */}
                  <div className="relative ml-auto" data-dropdown>
                    <button
                      onClick={() => setIsSortDropdownOpen(!isSortDropdownOpen)}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg border border-neutral-200 bg-white text-sm font-medium hover:bg-neutral-50"
                    >
                      Sort by
                      <ChevronDown className="h-4 w-4" />
                    </button>
                    {isSortDropdownOpen && (
                      <div className="absolute top-full right-0 mt-1 z-10 rounded-lg border border-neutral-200 bg-white shadow-lg">
                        {[
                          { key: 'newest', label: 'Newest first' },
                          { key: 'oldest', label: 'Oldest first' },
                          { key: 'name-asc', label: 'Candidate name A-Z' },
                          { key: 'opportunity-asc', label: 'Opportunity title A-Z' },
                        ].map((sort) => (
                          <button
                            key={sort.key}
                            onClick={() => {
                              setSortBy(sort.key);
                              setIsSortDropdownOpen(false);
                            }}
                            className={`w-full text-left px-4 py-2 text-sm hover:bg-neutral-50 ${sortBy === sort.key ? 'font-semibold text-blue-600' : ''}`}
                          >
                            {sort.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Applications Table */}
                {filteredApplications.length === 0 ? (
                  <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center">
                    <p className="text-neutral-600">
                      {searchTerm || selectedStatuses.length < 4
                        ? 'No applications match your filters.'
                        : 'No applications yet.'}
                    </p>
                  </div>
                ) : (
                  <OrganizationApplicationsTable
                    applications={filteredApplications}
                    onStatusChange={updateApplicationStatus}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default OrganizationAllApplicationsPage;
