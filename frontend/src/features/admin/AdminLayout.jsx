import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  BellRing,
  BriefcaseBusiness,
  CalendarClock,
  LayoutDashboard,
  LogOut,
  RadioTower,
  ShieldCheck,
  UsersRound,
} from 'lucide-react';

import { Button } from '../../components/ui/button.jsx';
import { adminLogout } from './adminAuthService.js';

const navItems = [
  {
    to: '/admin/dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    children: [
      {
        to: '/admin/dashboard/sources',
        label: 'Sources Monitoring',
        icon: RadioTower,
      },
      {
        to: '/admin/dashboard/scheduler',
        label: 'Scheduler Intelligence',
        icon: CalendarClock,
      },
      {
        to: '/admin/dashboard/pipeline',
        label: 'Pipeline Health',
        icon: Activity,
      },
      {
        to: '/admin/dashboard/alerts',
        label: 'Alerts',
        icon: BellRing,
      },
      {
        to: '/admin/dashboard/analytics',
        label: 'Analytics',
        icon: BarChart3,
      },
    ],
  },
  {
    to: '/admin/opportunities',
    label: 'Opportunities',
    icon: BriefcaseBusiness,
  },
  {
    to: '/admin/users',
    label: 'Users',
    icon: UsersRound,
  },
];

const AdminLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isDashboardSection = location.pathname.startsWith('/admin/dashboard');

  const handleLogout = () => {
    adminLogout();
    navigate('/admin/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-neutral-100 text-neutral-900">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-neutral-800 bg-neutral-950 text-neutral-100 lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-neutral-800 px-5">
          <div className="rounded-md bg-blue-500 p-2 text-white">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold">BidWise Admin</p>
            <p className="text-xs text-neutral-400">Backoffice</p>
          </div>
        </div>

        <nav className="space-y-1 px-3 py-4" aria-label="Admin navigation">
          {navItems.map(({ to, label, icon: Icon, children }) => (
            <div key={to}>
              <NavLink
                to={to}
                end={to === '/admin/dashboard'}
                className={({ isActive }) => {
                  const active = isActive || (to === '/admin/dashboard' && isDashboardSection);

                  return `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
                    active
                      ? 'bg-blue-500 text-white'
                      : 'text-neutral-300 hover:bg-neutral-900 hover:text-white'
                  }`;
                }}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </NavLink>

              {children && isDashboardSection ? (
                <div className="mt-1 space-y-1 border-l border-neutral-800 pl-4">
                  {children.map(({ to: childTo, label: childLabel, icon: ChildIcon }) => (
                    <NavLink
                      key={childTo}
                      to={childTo}
                      className={({ isActive }) =>
                        `flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition ${
                          isActive
                            ? 'bg-neutral-800 text-white'
                            : 'text-neutral-400 hover:bg-neutral-900 hover:text-white'
                        }`
                      }
                    >
                      <ChildIcon className="h-3.5 w-3.5" aria-hidden="true" />
                      {childLabel}
                    </NavLink>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-40 border-b border-neutral-200 bg-white">
          <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-neutral-100 p-2 text-neutral-700 lg:hidden">
                <ShieldCheck className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold text-neutral-900">Admin workspace</p>
                <p className="text-xs text-neutral-500">Operational control panel</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button type="button" variant="outline" onClick={handleLogout}>
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Logout
              </Button>
            </div>
          </div>
        </header>

        <nav className="border-b border-neutral-200 bg-white px-4 py-2 sm:px-6 lg:hidden" aria-label="Admin mobile navigation">
          <div className="flex gap-2 overflow-x-auto">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/admin/dashboard'}
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
                    isActive || (to === '/admin/dashboard' && isDashboardSection)
                      ? 'bg-blue-600 text-white'
                      : 'text-neutral-700 hover:bg-neutral-100'
                  }`
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </div>
          {isDashboardSection ? (
            <div className="mt-2 flex gap-2 overflow-x-auto">
              {navItems[0].children.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `inline-flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition ${
                      isActive
                        ? 'bg-neutral-900 text-white'
                        : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-950'
                    }`
                  }
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {label}
                </NavLink>
              ))}
            </div>
          ) : null}
        </nav>

        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
