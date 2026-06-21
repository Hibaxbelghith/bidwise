import { useCallback, useEffect, useState } from 'react';
import { fetchMyApplications, withdrawApplication } from '../services/applicationsservice';

const useMyApplications = ({ enabled = true } = {}) => {
  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    if (!enabled) {
      setApplications([]);
      setIsLoading(false);
      setError('');
      return () => {
        cancelled = true;
      };
    }

    setIsLoading(true);
    fetchMyApplications()
      .then((data) => { if (!cancelled) setApplications(data); })
      .catch(() => { if (!cancelled) setError('Unable to load your applications.'); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [enabled]);

  const withdraw = useCallback(async (id) => {
    if (!enabled) return;
    await withdrawApplication(id);
    setApplications((prev) =>
      prev.map((app) => app.id === id ? { ...app, statut: 'WITHDRAWN' } : app)
    );
  }, [enabled]);

  return { applications, isLoading, error, withdraw };
};

export default useMyApplications;
