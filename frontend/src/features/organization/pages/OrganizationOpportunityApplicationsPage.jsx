import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { useParams, Navigate } from 'react-router-dom';
import { Users } from 'lucide-react';

import { Spinner } from '../../../components/ui/spinner.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import ApplicationCard from '../components/ApplicationCard.jsx';
import {
  getOrganizationOpportunity,
  getOpportunityApplications,
} from '../services/organizationService.js';

const OrganizationOpportunityApplicationsPage = () => {
  const { loading, user } = useAuth();
  const profile = user?.organization_profile;
  const { opportunityId } = useParams();

  const [opportunity, setOpportunity] = useState(null);
  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState('all');

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, []);

  useEffect(() => {
    let isCancelled = false;

    if (!isOrganizationProfileComplete(profile)) {
      return undefined;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError('');

        // Fetch opportunity details
        const oppData = await getOrganizationOpportunity(opportunityId);
        if (!isCancelled) {
          setOpportunity(oppData);
        }

        // Fetch applications
        const appData = await getOpportunityApplications(opportunityId);
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
  }, [profile, opportunityId]);

  // Filter applications based on selected filter
  const filteredApplications = useMemo(() => {
    if (selectedFilter === 'all') {
      return applications;
    }
    if (selectedFilter === 'new') {
      return applications.filter(app => app.statut === 'SUBMITTED');
    }
    if (selectedFilter === 'rejected') {
      return applications.filter(app => app.statut === 'REJECTED');
    }
    return applications;
  }, [applications, selectedFilter]);

  // Count applications by status
  const counts = useMemo(() => ({
    all: applications.length,
    new: applications.filter(app => app.statut === 'SUBMITTED').length,
    rejected: applications.filter(app => app.statut === 'REJECTED').length,
  }), [applications]);

  // Handle rejection - update status locally without reloading
  const handleReject = (applicationId) => {
    setApplications(prev =>
      prev.map(app =>
        app.id === applicationId ? { ...app, statut: 'REJECTED' } : app
      )
    );
  };

  if (loading) {
    return <Spinner className="h-screen" />;
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  const activePath = '/organization/applications';
  const opportunityTitle = opportunity?.titre || 'Loading...';

  return (
    <div className="flex h-screen overflow-hidden bg-neutral-50">
      <OrganizationSidebar
        activePath={activePath}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      <main className="flex-1 overflow-y-auto">
        <div className="border-b border-neutral-200 bg-[#efeeec] px-5 py-4">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-neutral-900">
            <Users className="h-7 w-7" />
            Applications — {opportunityTitle}
          </h1>
        </div>

        <div className="p-5">
          {isLoading && <Spinner />}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
              {error}
            </div>
          )}
          {!isLoading && !error && applications.length === 0 && (
            <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center">
              <p className="text-neutral-600">No applications received yet.</p>
            </div>
          )}
          {!isLoading && !error && applications.length > 0 && (
            <>
              {/* Filter Tabs */}
              <div className="mb-6 flex items-center gap-6 border-b border-neutral-200 pb-3">
                {[
                  { key: 'all', label: 'All', count: counts.all },
                  { key: 'new', label: 'New', count: counts.new },
                  { key: 'rejected', label: 'Rejected', count: counts.rejected },
                ].map((filter) => (
                  <button
                    key={filter.key}
                    onClick={() => setSelectedFilter(filter.key)}
                    className={`font-medium text-sm transition-colors ${
                      selectedFilter === filter.key
                        ? 'text-neutral-900 border-b-2 border-neutral-900 pb-3'
                        : 'text-neutral-600 hover:text-neutral-900'
                    }`}
                  >
                    {filter.label} ({filter.count})
                  </button>
                ))}
              </div>

              {/* Application List */}
              {filteredApplications.length === 0 ? (
                <div className="rounded-lg border border-neutral-200 bg-white p-8 text-center">
                  <p className="text-neutral-600">No applications in this category.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredApplications.map((application) => (
                    <ApplicationCard
                      key={application.id}
                      application={application}
                      opportunityId={opportunityId}
                      onReject={handleReject}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default OrganizationOpportunityApplicationsPage;
