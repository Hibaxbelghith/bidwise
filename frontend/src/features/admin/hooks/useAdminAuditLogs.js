import { useCallback, useEffect, useState } from 'react';
import adminApi from '../../../lib/adminApi.js';
import { useApiErrorParser } from './useApiErrorParser.js';

const normalizePaginatedResponse = (data) => ({
  results: Array.isArray(data?.results) ? data.results : [],
  count: Number(data?.count || 0),
  next: data?.next || null,
  previous: data?.previous || null,
});

export const AUDIT_ACTION_OPTIONS = [
  { value: '', label: 'All actions' },
  { value: 'SUSPEND', label: 'Suspensions' },
  { value: 'REACTIVATE', label: 'Reactivations' },
  { value: 'TOGGLE_ADMIN', label: 'Role changes' },
  { value: 'TOGGLE_ACTIVE', label: 'Active status changes' },
  { value: 'APPROVE_ORG_OPPORTUNITY', label: 'Opportunity approvals' },
  { value: 'REJECT_ORG_OPPORTUNITY', label: 'Opportunity rejections' },
];

export const useAdminAuditLogs = ({ action, page, pageSize }) => {
  const { parseError } = useApiErrorParser();
  const [logs, setLogs] = useState([]);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadLogs = useCallback(async ({ signal } = {}) => {
    setIsLoading(true);
    setError('');
    try {
      const params = { page, page_size: pageSize };
      if (action) params.action = action;
      const { data } = await adminApi.get('/admin/audit-logs/', { params, signal });
      const normalized = normalizePaginatedResponse(data);
      setLogs(normalized.results);
      setCount(normalized.count);
      setHasNext(Boolean(normalized.next));
      setHasPrevious(Boolean(normalized.previous));
    } catch (requestError) {
      if (requestError?.code === 'ERR_CANCELED') return;
      const parsed = parseError(requestError);
      setError(parsed.message || 'Unable to load audit log.');
    } finally {
      if (!signal?.aborted) setIsLoading(false);
    }
  }, [action, page, pageSize, parseError]);

  useEffect(() => {
    const controller = new AbortController();
    loadLogs({ signal: controller.signal });
    return () => controller.abort();
  }, [loadLogs]);

  const exportCsv = useCallback(async () => {
    const params = {};
    if (action) params.action = action;
    const response = await adminApi.get('/admin/audit-logs/export/', {
      params,
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'bidwise-admin-audit-log.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }, [action]);

  const exportPdf = useCallback(async () => {
    const params = {};
    if (action) params.action = action;
    const response = await adminApi.get('/admin/audit-logs/export-pdf/', {
      params,
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'bidwise-admin-audit-log.pdf';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }, [action]);

  return {
    logs,
    count,
    hasNext,
    hasPrevious,
    isLoading,
    error,
    exportCsv,
    exportPdf,
    reload: loadLogs,
  };
};
