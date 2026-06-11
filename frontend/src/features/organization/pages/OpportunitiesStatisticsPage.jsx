import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { BarChart3, Briefcase, Users, Eye, Calendar, TrendingUp, DollarSign, MessageSquare } from 'lucide-react';

import { Spinner } from '../../../components/ui/spinner.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import { listOrganizationOpportunities } from '../services/organizationService.js';
import { getOpportunitiesApplicationsStats } from '../services/organizationService.js';
import StatisticsOverview from '../components/StatisticsOverview.jsx';
import MostPopularOpportunity from '../components/MostPopularOpportunity.jsx';

const OpportunitiesStatisticsPage = () => {
  const { loading, user } = useAuth();
  const profile = user?.organization_profile;
  const [opportunities, setOpportunities] = useState([]);
  const [applicationsData, setApplicationsData] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, []);

  useEffect(() => {
    let isCancelled = false;

    if (!isOrganizationProfileComplete(profile)) {
      setOpportunities([]);
      return undefined;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError('');
        const opps = await listOrganizationOpportunities();
        if (!isCancelled) {
          setOpportunities(opps);
          const stats = await getOpportunitiesApplicationsStats(opps);
          if (!isCancelled) {
            setApplicationsData(stats);
          }
        }
      } catch (err) {
        if (!isCancelled) {
          setError(err?.response?.data?.detail || 'Failed to load opportunities');
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

  const stats = useMemo(() => {
    const totalOpportunities = opportunities.length;
    const activeOpportunities = opportunities.filter(
      (opp) => opp.status === 'ACTIVE' || opp.statut === 'ACTIVE'
    ).length;
    
    const totalApplications = opportunities.reduce(
      (sum, opp) => sum + (opp.applications_count || 0),
      0
    );
    
    const newApplications = opportunities.reduce(
      (sum, opp) => sum + (opp.new_applications_count || 0),
      0
    );

    const viewsCount = opportunities.reduce(
      (sum, opp) => sum + (opp.views_count || 0),
      0
    );

    return {
      totalOpportunities,
      activeOpportunities,
      totalApplications,
      newApplications,
      viewsCount,
    };
  }, [opportunities, applicationsData]);

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-white px-4">
        <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-5 py-4 text-sm text-gray-600">
          <Spinner size={16} className="text-blue-600" />
          Loading statistics
        </div>
      </section>
    );
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-white" aria-labelledby="statistics-heading">
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[auto_1fr]">
        <OrganizationSidebar 
          activePath="/organization/statistics" 
          isCollapsed={isSidebarCollapsed} 
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)} 
        />

        <div className="min-w-0">
        

          <div className="p-6">
            {error && (
              <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {isLoading ? (
              <div className="flex min-h-[400px] items-center justify-center">
                <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-5 py-4 text-sm text-gray-600">
                  <Spinner size={16} className="text-blue-600" />
                  Loading your statistics
                </div>
              </div>
            ) : opportunities.length === 0 ? (
              <div className="flex min-h-[400px] flex-col items-center justify-center text-center">
                <div className="rounded-full bg-gray-100 p-4 mb-4">
                  <Briefcase className="h-12 w-12 text-gray-400" />
                </div>
                <p className="text-gray-600">No opportunities yet</p>
                <p className="mt-1 text-sm text-gray-400">
                  Create your first opportunity to see statistics
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Stats Grid - Simple cards */}
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Total opportunities</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900">{stats.totalOpportunities}</p>
                      </div>
                      <div className="rounded-lg bg-blue-50 p-2">
                        <Briefcase className="h-5 w-5 text-blue-600" />
                      </div>
                    </div>
                    <div className="mt-3 text-xs text-gray-400">
                      {stats.activeOpportunities} active
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Total applications</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900">{stats.totalApplications}</p>
                      </div>
                      <div className="rounded-lg bg-blue-50 p-2">
                        <Users className="h-5 w-5 text-blue-600" />
                      </div>
                    </div>
                    <div className="mt-3 text-xs text-gray-400">
                      Across all opportunities
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">New applications</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900">{stats.newApplications}</p>
                      </div>
                      <div className="rounded-lg bg-blue-50 p-2">
                        <Calendar className="h-5 w-5 text-blue-600" />
                      </div>
                    </div>
                    <div className="mt-3 text-xs text-gray-400">
                      Last 30 days
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">Profile views</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900">{stats.viewsCount}</p>
                      </div>
                      <div className="rounded-lg bg-blue-50 p-2">
                        <Eye className="h-5 w-5 text-blue-600" />
                      </div>
                    </div>
                    <div className="mt-3 text-xs text-gray-400">
                      Total impressions
                    </div>
                  </div>
                </div>

                

                {/* Most Popular Opportunity Section */}
                <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
                  <div className="border-b border-gray-100 bg-white px-5 py-3">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-blue-600" />
                      <h2 className="text-base font-medium text-gray-900">Most popular opportunity</h2>
                    </div>
                  </div>
                  <div className="p-5">
                    <MostPopularOpportunity 
                      opportunities={opportunities}
                      applicationsData={applicationsData}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </section>
  );
};

export default OpportunitiesStatisticsPage;