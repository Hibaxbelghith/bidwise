import { useEffect } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

const ScrollManager = () => {
  const { pathname, state } = useLocation();
  const navigationType = useNavigationType();

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const isControlledReturnToOpportunities =
      pathname === '/opportunities' &&
      (state?.returnTab || Number.isFinite(Number(state?.scrollY)));

    if (isControlledReturnToOpportunities) {
      return;
    }

    if (navigationType === 'PUSH') {
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    }
  }, [pathname, navigationType, state]);

  return null;
};

export default ScrollManager;
