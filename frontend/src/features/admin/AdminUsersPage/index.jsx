import { useState } from 'react';

import AdminAuditLogTab from './AdminAuditLogTab.jsx';
import AdminUsersFilters from './AdminUsersFilters.jsx';
import AdminUsersPagination from './AdminUsersPagination.jsx';
import AdminUsersTable from './AdminUsersTable.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import { useAdminUsers } from '../hooks/useAdminUsers.js';
import { PAGE_SIZE_OPTIONS, useAdminUsersFilters } from '../hooks/useAdminUsersFilters.js';

const TABS = [
  { value: 'users', label: 'Users list' },
  { value: 'audit', label: 'Audit log' },
];

const AdminUsersPage = () => {
  const { user: currentAdminUser } = useAuth();
  const [activeTab, setActiveTab] = useState('users');
  const filters = useAdminUsersFilters();
  const {
    users,
    count,
    hasNext,
    hasPrevious,
    isLoading,
    isInitialLoading,
    isRefreshing,
    error,
    actionUserId,
    toggleAdmin,
    suspendUser,
    reactivateUser,
  } = useAdminUsers(filters);

  const totalPages = Math.max(Math.ceil(count / filters.pageSize), 1);

  return (
    <section className="bg-neutral-50" aria-labelledby="admin-users-heading">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 id="admin-users-heading" className="text-3xl font-bold text-neutral-900">
            User management
          </h1>
          <p className="mt-2 text-sm text-neutral-600">
            Manage BidWise accounts, admin privileges, suspensions, and audit traceability.
          </p>
        </div>

        <div className="mb-6 inline-flex rounded-lg border border-neutral-200 bg-white p-1 shadow-sm">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => setActiveTab(tab.value)}
              className={[
                'rounded-md px-4 py-2 text-sm font-medium transition',
                activeTab === tab.value
                  ? 'bg-neutral-950 text-white'
                  : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-950',
              ].join(' ')}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'users' ? (
          <>
            {error ? (
              <div className="mb-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
                {error}
              </div>
            ) : null}

            <AdminUsersFilters
              searchDraft={filters.searchDraft}
              onSearchDraftChange={filters.setSearchDraft}
              role={filters.role}
              status={filters.status}
              provider={filters.provider}
              joinedAfter={filters.joinedAfter}
              joinedBefore={filters.joinedBefore}
              lastLoginAfter={filters.lastLoginAfter}
              lastLoginBefore={filters.lastLoginBefore}
              activeAdvancedFilters={filters.activeAdvancedFilters}
              onUpdateQueryParams={filters.updateQueryParams}
              onResetFilters={filters.resetFilters}
            />

            <div className="mt-6">
              <AdminUsersTable
                users={users}
                count={count}
                ordering={filters.ordering}
                onToggleOrdering={filters.toggleOrdering}
                isLoading={isLoading}
                isInitialLoading={isInitialLoading}
                isRefreshing={isRefreshing}
                actionUserId={actionUserId}
                currentAdminUser={currentAdminUser}
                onToggleAdmin={toggleAdmin}
                onSuspendUser={suspendUser}
                onReactivateUser={reactivateUser}
              />
            </div>

            <AdminUsersPagination
              page={filters.page}
              totalPages={totalPages}
              pageSize={filters.pageSize}
              pageSizeOptions={PAGE_SIZE_OPTIONS}
              hasNext={hasNext}
              hasPrevious={hasPrevious}
              isLoading={isLoading}
              onChangePage={(nextPage) => filters.updateQueryParams({ page: nextPage })}
              onChangePageSize={(nextPageSize) => filters.updateQueryParams(
                { page_size: nextPageSize },
                { resetPage: true },
              )}
            />
          </>
        ) : (
          <AdminAuditLogTab />
        )}
      </div>
    </section>
  );
};

export default AdminUsersPage;
