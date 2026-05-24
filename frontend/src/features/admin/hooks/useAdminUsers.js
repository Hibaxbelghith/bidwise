import { useCallback, useEffect, useRef, useState } from 'react';
import adminApi from '../../../lib/adminApi.js';
import { useApiErrorParser } from './useApiErrorParser.js';

const normalizePaginatedResponse = (data) => {
  if (Array.isArray(data)) {
    return {
      results: data,
      count: data.length,
      next: null,
      previous: null,
    };
  }

  return {
    results: Array.isArray(data?.results) ? data.results : [],
    count: Number(data?.count || 0),
    next: data?.next || null,
    previous: data?.previous || null,
  };
};

const isRequestCanceled = (error) => error?.code === 'ERR_CANCELED';

const shouldRetryRequest = (error) => {
  const status = error?.response?.status;
  if (status === 401) return false;
  if (!status) return Boolean(error?.request);
  return status >= 500;
};

const wait = (ms, signal) => new Promise((resolve) => {
  const timeout = window.setTimeout(resolve, ms);
  if (!signal) return;
  signal.addEventListener('abort', () => {
    window.clearTimeout(timeout);
    resolve();
  }, { once: true });
});

export const useAdminUsers = ({
  page,
  pageSize,
  search,
  role,
  status,
  provider,
  joinedAfter,
  joinedBefore,
  lastLoginAfter,
  lastLoginBefore,
  ordering,
}) => {
  const { parseError } = useApiErrorParser();
  const [users, setUsers] = useState([]);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [actionUserId, setActionUserId] = useState(null);

  const latestRequestId = useRef(0);
  const usersRef = useRef([]);

  useEffect(() => {
    usersRef.current = users;
  }, [users]);

  const loadUsers = useCallback(async ({ signal } = {}) => {
    const requestId = latestRequestId.current + 1;
    latestRequestId.current = requestId;

    setIsLoading(true);

    const params = {
      page,
      page_size: pageSize,
    };
    if (search) params.search = search;
    if (role) params.role = role;
    if (status) params.status = status;
    if (provider) params.provider = provider;
    if (joinedAfter) params.joined_after = joinedAfter;
    if (joinedBefore) params.joined_before = joinedBefore;
    if (lastLoginAfter) params.last_login_after = lastLoginAfter;
    if (lastLoginBefore) params.last_login_before = lastLoginBefore;
    if (ordering) params.ordering = ordering;

    let lastError;

    try {
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          const { data } = await adminApi.get('/admin/users/', { params, signal });
          if (latestRequestId.current !== requestId) return;

          const normalized = normalizePaginatedResponse(data);
          setUsers(normalized.results);
          setCount(normalized.count);
          setHasNext(Boolean(normalized.next));
          setHasPrevious(Boolean(normalized.previous));
          return;
        } catch (requestError) {
          lastError = requestError;

          if (isRequestCanceled(requestError)) return;
          if (latestRequestId.current !== requestId) return;

          const canRetry = attempt === 0
            && shouldRetryRequest(requestError)
            && !signal?.aborted;

          if (!canRetry) {
            if (usersRef.current.length === 0) {
              setUsers([]);
              setCount(0);
              setHasNext(false);
              setHasPrevious(false);
            }
            return;
          }

          await wait(500, signal);
          if (signal?.aborted) return;
        }
      }

      if (lastError && latestRequestId.current === requestId) {
        // Just log, error handling is done by component via toast
        console.error('Load users error:', lastError);
      }
    } finally {
      if (latestRequestId.current === requestId && !signal?.aborted) {
        setIsLoading(false);
      }
    }
  }, [joinedAfter, joinedBefore, lastLoginAfter, lastLoginBefore, ordering, page, pageSize, provider, role, search, status]);

  useEffect(() => {
    const controller = new AbortController();
    loadUsers({ signal: controller.signal });
    return () => controller.abort();
  }, [loadUsers]);

  const updateUserInList = useCallback((updatedUser) => {
    setUsers((currentUsers) => (
      currentUsers.map((user) => (user.id === updatedUser.id ? updatedUser : user))
    ));
  }, []);

  const toggleAdmin = useCallback(async (user) => {
    try {
      setActionUserId(user.id);
      const { data } = await adminApi.post(`/admin/users/${user.id}/toggle-admin/`);
      updateUserInList(data);
      await loadUsers();
      return { success: true, data };
    } catch (error) {
      const parsed = parseError(error);
      return { success: false, error: parsed };
    } finally {
      setActionUserId(null);
    }
  }, [loadUsers, updateUserInList, parseError]);

  const toggleActive = useCallback(async (user) => {
    try {
      setActionUserId(user.id);
      const { data } = await adminApi.post(`/admin/users/${user.id}/toggle-active/`);
      updateUserInList(data);
      await loadUsers();
      return { success: true, data };
    } catch (error) {
      const parsed = parseError(error);
      return { success: false, error: parsed };
    } finally {
      setActionUserId(null);
    }
  }, [loadUsers, updateUserInList, parseError]);

  const suspendUser = useCallback(async (user, reason, detail = '') => {
    try {
      setActionUserId(user.id);
      const { data } = await adminApi.post(`/admin/users/${user.id}/suspend/`, { 
        reason,
        detail: detail || '',
      });
      updateUserInList(data);
      await loadUsers();
      return { success: true, data };
    } catch (error) {
      const parsed = parseError(error);
      return { success: false, error: parsed };
    } finally {
      setActionUserId(null);
    }
  }, [loadUsers, updateUserInList, parseError]);

  const reactivateUser = useCallback(async (user) => {
    try {
      setActionUserId(user.id);
      const { data } = await adminApi.post(`/admin/users/${user.id}/reactivate/`);
      updateUserInList(data);
      await loadUsers();
      return { success: true, data };
    } catch (error) {
      const parsed = parseError(error);
      return { success: false, error: parsed };
    } finally {
      setActionUserId(null);
    }
  }, [loadUsers, updateUserInList, parseError]);

  const isInitialLoading = isLoading && users.length === 0;
  const isRefreshing = isLoading && users.length > 0;

  return {
    users,
    count,
    hasNext,
    hasPrevious,
    isLoading,
    isInitialLoading,
    isRefreshing,
    actionUserId,
    reload: loadUsers,
    toggleAdmin,
    toggleActive,
    suspendUser,
    reactivateUser,
  };
};