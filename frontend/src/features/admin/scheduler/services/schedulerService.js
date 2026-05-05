import adminApi from '../../../../lib/adminApi.js';

export * from './schedulerDecisionService.js';

export const getSchedulerState = ({ signal } = {}) => (
  adminApi.get('/admin/scheduler-state/', { signal })
);
