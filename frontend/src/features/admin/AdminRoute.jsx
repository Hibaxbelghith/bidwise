import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { validateAdminSession } from './adminAuthService.js';
import { hasAdminSession, removeAdminTokens } from './adminTokenManager.js';

const AdminRoute = () => {
  const location = useLocation();
  const [status, setStatus] = useState(() => (
    hasAdminSession() ? 'checking' : 'denied'
  ));

  useEffect(() => {
    if (status !== 'checking') {
      return undefined;
    }

    let isMounted = true;

    const checkAdminAccess = async () => {
      try {
        await validateAdminSession();
        if (isMounted) {
          setStatus('allowed');
        }
      } catch {
        removeAdminTokens();
        if (isMounted) {
          setStatus('denied');
        }
      }
    };

    checkAdminAccess();

    return () => {
      isMounted = false;
    };
  }, [status]);

  if (status === 'checking') {
    return null;
  }

  if (status === 'denied') {
    return <Navigate to="/admin/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
};

export default AdminRoute;
