import { useEffect, useState } from 'react';

import { getSchedulerState, normalizeSchedulerState } from '../services/schedulerService.js';

export const useScheduler = () => {
  const [schedulerState, setSchedulerState] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();

    const loadSchedulerState = async () => {
      try {
        setIsLoading(true);
        setError('');
        const { data } = await getSchedulerState({ signal: controller.signal });
        setSchedulerState(normalizeSchedulerState(data));
      } catch (requestError) {
        if (requestError.code === 'ERR_CANCELED') return;
        setError(requestError.response?.data?.detail || 'Unable to load scheduler state.');
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    loadSchedulerState();

    return () => {
      controller.abort();
    };
  }, []);

  return {
    schedulerState,
    isLoading,
    error,
  };
};
