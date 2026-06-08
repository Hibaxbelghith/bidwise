import { useEffect, useLayoutEffect, useState } from 'react';
import { Navigate, useParams } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext.jsx';
import OrganizationOpportunityDetailHeader from '../components/OrganizationOpportunityDetailHeader.jsx';
import OrganizationOpportunityDetails from '../components/OrganizationOpportunityDetails.jsx';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import {
  OrganizationOpportunityStatusDialog,
  statusFallbackForAction,
} from '../components/OrganizationOpportunityStatus.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';
import {
  changeOrganizationOpportunityStatus,
  getOrganizationOpportunity,
} from '../services/organizationService.js';

const OrganizationOpportunityDetailPage = () => {
  const { opportunityId } = useParams();
  const { loading, user } = useAuth();
  const profile = user?.organization_profile;
  const [opportunity, setOpportunity] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [pendingStatusAction, setPendingStatusAction] = useState(null);
  const [statusActionId, setStatusActionId] = useState(null);

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, []);

  useEffect(() => {
    if (!isOrganizationProfileComplete(profile)) return undefined;
    const controller = new AbortController();
    setIsLoading(true);
    setLoadError('');

    getOrganizationOpportunity(opportunityId, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setOpportunity(data);
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        setLoadError(error?.response?.status === 404
          ? 'This opportunity was not found in your organization workspace.'
          : 'Unable to load this opportunity. Please try again.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, [opportunityId, profile]);

  const applyStatusAction = async (currentOpportunity, action) => {
    try {
      setStatusActionId(currentOpportunity.id);
      setLoadError('');
      const result = await changeOrganizationOpportunityStatus(currentOpportunity.id, action);
      const serverOpportunity = result?.opportunity;
      setOpportunity((current) => ({
        ...current,
        ...(serverOpportunity || {}),
        status: serverOpportunity?.status || statusFallbackForAction(currentOpportunity, action),
      }));
      setPendingStatusAction(null);
    } catch (error) {
      setLoadError(error?.response?.data?.detail || 'Unable to update opportunity status.');
    } finally {
      setStatusActionId(null);
    }
  };

  const handleStatusAction = (currentOpportunity, action) => {
    if (action === 'activate') {
      applyStatusAction(currentOpportunity, action);
      return;
    }
    setPendingStatusAction({ opportunity: currentOpportunity, action });
  };

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-neutral-50 px-4">
        <p className="text-sm text-neutral-600">Loading organization workspace</p>
      </section>
    );
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-[#f4f3f1]">
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[286px_1fr]">
        <OrganizationSidebar activePath="/organization/dashboard" />
        <div className="min-w-0">
          {loadError ? (
            <div className="m-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {loadError}
            </div>
          ) : null}

          {isLoading ? (
            <div className="flex min-h-[65vh] items-center justify-center">
              <p className="text-sm font-medium text-neutral-600">Loading opportunity details</p>
            </div>
          ) : opportunity ? (
            <>
              <OrganizationOpportunityDetailHeader
                opportunity={opportunity}
                organizationName={profile.organization_name}
                statusActionId={statusActionId}
                onStatusAction={handleStatusAction}
              />
              <OrganizationOpportunityDetails opportunity={opportunity} />
            </>
          ) : null}
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

export default OrganizationOpportunityDetailPage;
