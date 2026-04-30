import { useCallback, useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, ShieldCheck, ShieldOff, UserCheck, UserX } from 'lucide-react';

import { Badge } from '../../components/ui/badge.jsx';
import { Button } from '../../components/ui/button.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table.jsx';
import adminApi from '../../lib/adminApi.js';

const PAGE_SIZE = 20;

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

const roleClassName = (isAdmin) => (
  isAdmin
    ? 'border-blue-200 bg-blue-50 text-blue-700'
    : 'border-neutral-200 bg-neutral-50 text-neutral-700'
);

const statusClassName = (isActive) => (
  isActive
    ? 'border-green-200 bg-green-50 text-green-700'
    : 'border-red-200 bg-red-50 text-red-700'
);

const AdminUsersPage = () => {
  const [users, setUsers] = useState([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionUserId, setActionUserId] = useState(null);

  const totalPages = Math.max(Math.ceil(count / PAGE_SIZE), 1);

  const loadUsers = useCallback(async () => {
    try {
      setIsLoading(true);
      setError('');
      const { data } = await adminApi.get('/admin/users/', { params: { page } });
      const normalized = normalizePaginatedResponse(data);
      setUsers(normalized.results);
      setCount(normalized.count);
      setHasNext(Boolean(normalized.next));
      setHasPrevious(Boolean(normalized.previous));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to load users.');
      setUsers([]);
      setCount(0);
      setHasNext(false);
      setHasPrevious(false);
    } finally {
      setIsLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const updateUserInList = (updatedUser) => {
    setUsers((currentUsers) => (
      currentUsers.map((user) => (user.id === updatedUser.id ? updatedUser : user))
    ));
  };

  const handleToggleAdmin = async (user) => {
    const confirmed = window.confirm(`Change admin role for ${user.email}?`);
    if (!confirmed) return;

    try {
      setActionUserId(user.id);
      setError('');
      const { data } = await adminApi.post(`/admin/users/${user.id}/toggle-admin/`);
      updateUserInList(data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to update user role.');
    } finally {
      setActionUserId(null);
    }
  };

  const handleToggleActive = async (user) => {
    const action = user.is_active ? 'disable' : 'activate';
    const confirmed = window.confirm(`Do you want to ${action} ${user.email}?`);
    if (!confirmed) return;

    try {
      setActionUserId(user.id);
      setError('');
      const { data } = await adminApi.post(`/admin/users/${user.id}/toggle-active/`);
      updateUserInList(data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to update user status.');
    } finally {
      setActionUserId(null);
    }
  };

  return (
    <section className="bg-neutral-50" aria-labelledby="admin-users-heading">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 id="admin-users-heading" className="text-3xl font-bold text-neutral-900">
            Users
          </h1>
          <p className="mt-2 text-sm text-neutral-600">Manage account access and admin privileges.</p>
        </div>

        {error ? (
          <div className="mb-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
            {error}
          </div>
        ) : null}

        <Card>
          <CardHeader className="flex flex-col gap-2 border-b border-neutral-200 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-base">User list</CardTitle>
            <span className="text-sm text-neutral-500">{count} total</span>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-neutral-50">
                  <TableHead className="px-4 py-3">Email</TableHead>
                  <TableHead className="px-4 py-3">Role</TableHead>
                  <TableHead className="px-4 py-3">Status</TableHead>
                  <TableHead className="px-4 py-3 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="px-4 py-10 text-center text-neutral-500">
                      Loading users...
                    </TableCell>
                  </TableRow>
                ) : null}

                {!isLoading && users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="px-4 py-10 text-center text-neutral-500">
                      No users found.
                    </TableCell>
                  </TableRow>
                ) : null}

                {!isLoading && users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="max-w-[460px] px-4 py-3">
                      <p className="truncate font-medium text-neutral-900">{user.email || `User #${user.id}`}</p>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <Badge variant="outline" className={roleClassName(user.is_admin)}>
                        {user.is_admin ? 'ADMIN' : 'USER'}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <Badge variant="outline" className={statusClassName(user.is_active)}>
                        {user.is_active ? 'ACTIVE' : 'DISABLED'}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={actionUserId === user.id}
                          onClick={() => handleToggleAdmin(user)}
                        >
                          {user.is_admin ? (
                            <ShieldOff className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                          )}
                          {user.is_admin ? 'Make user' : 'Make admin'}
                        </Button>
                        <Button
                          type="button"
                          variant={user.is_active ? 'destructive' : 'outline'}
                          size="sm"
                          disabled={actionUserId === user.id}
                          onClick={() => handleToggleActive(user)}
                        >
                          {user.is_active ? (
                            <UserX className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <UserCheck className="h-4 w-4" aria-hidden="true" />
                          )}
                          {user.is_active ? 'Disable' : 'Activate'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-neutral-500">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!hasPrevious || isLoading}
              onClick={() => setPage((currentPage) => Math.max(currentPage - 1, 1))}
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              Prev
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!hasNext || isLoading}
              onClick={() => setPage((currentPage) => currentPage + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default AdminUsersPage;
