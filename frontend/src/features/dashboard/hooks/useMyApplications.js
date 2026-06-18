import { useCallback, useEffect, useState } from 'react';
import { fetchMyApplications, withdrawApplication } from '../services/applicationsservice';

const useMyApplications = () => {
  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    fetchMyApplications()
      .then((data) => { if (!cancelled) setApplications(data); })
      .catch(() => { if (!cancelled) setError('Unable to load your applications.'); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const withdraw = useCallback(async (id) => {
    await withdrawApplication(id);
    setApplications((prev) =>
      prev.map((app) => app.id === id ? { ...app, statut: 'WITHDRAWN' } : app)
    );
  }, []);

  return { applications, isLoading, error, withdraw };
};

export default useMyApplications;
