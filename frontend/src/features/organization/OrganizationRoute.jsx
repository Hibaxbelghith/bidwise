import { Navigate, Outlet } from 'react-router-dom';

import { Spinner } from '../../components/ui/spinner.jsx';
import { useAuth } from '../auth/AuthContext.jsx';
import {
  ORGANIZATION_LOGIN_PATH,
  isOrganizationAccount,
} from './organizationFlow.js';

const OrganizationRoute = ({ requireOrganizationAccount = false }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-neutral-50 px-4">
        <div className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-600">
          <Spinner size={16} className="text-emerald-700" />
          Preparing organization workspace
        </div>
      </section>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={ORGANIZATION_LOGIN_PATH} replace />;
  }

  if (requireOrganizationAccount && !isOrganizationAccount(user)) {
    return <Navigate to="/organizations" replace />;
  }

  return <Outlet />;
};

export default OrganizationRoute;
