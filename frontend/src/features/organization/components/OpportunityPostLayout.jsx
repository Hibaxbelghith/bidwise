import { Navigate } from 'react-router-dom';

import { Spinner } from '../../../components/ui/spinner.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import OrganizationSidebar from './OrganizationSidebar.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';

const OpportunityPostLayout = ({
  eyebrow,
  title,
  description,
  headingId,
  children,
}) => {
  const { user, loading } = useAuth();
  const profile = user?.organization_profile;

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-white px-4">
        <div className="flex items-center gap-3 rounded-lg border border-neutral-200 px-5 py-4 text-sm text-neutral-600">
          <Spinner size={16} className="text-blue-700" />
          Preparing organization workspace
        </div>
      </section>
    );
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-white" aria-labelledby={headingId}>
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[286px_1fr]">
        <OrganizationSidebar activePath="/organization/post" />
        <main className="min-w-0">
          <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl flex-col px-5 py-10">
            <div className="text-center">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">{eyebrow}</p>
              <h1 id={headingId} className="mt-3 text-4xl font-semibold tracking-tight text-neutral-950">
                {title}
              </h1>
              {description ? <p className="mt-4 text-sm text-neutral-600">{description}</p> : null}
            </div>
            {children}
          </div>
        </main>
      </div>
    </section>
  );
};

export default OpportunityPostLayout;
