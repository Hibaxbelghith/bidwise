import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { AUTH_REDIRECT_EVENT } from './authSessionEvents.js';

const AuthRedirectBridge = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const handleAuthRedirect = (event) => {
      const redirectPath = event?.detail?.redirectPath || '/login';
      if (location.pathname === redirectPath) return;

      navigate(redirectPath, {
        replace: true,
        state: { authReason: event?.detail?.reason || 'session_expired' },
      });
    };

    window.addEventListener(AUTH_REDIRECT_EVENT, handleAuthRedirect);
    return () => {
      window.removeEventListener(AUTH_REDIRECT_EVENT, handleAuthRedirect);
    };
  }, [location.pathname, navigate]);

  return null;
};

export default AuthRedirectBridge;
