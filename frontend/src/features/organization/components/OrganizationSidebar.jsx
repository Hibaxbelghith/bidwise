import { Link } from 'react-router-dom';
import {
  BarChart3,
  BriefcaseBusiness,
  CalendarDays,
  ChevronRight,
  Folder,
  Plus,
  Search,
  Users,
  X,
} from 'lucide-react';

const navItems = [
  { label: 'Create', icon: Plus, href: '/organization/post', prominent: true, match: '/organization/post' },
  { label: 'Jobs', icon: BriefcaseBusiness, href: '/organization/dashboard', match: '/organization/dashboard' },
  { label: 'Applications', icon: Users, href: '/organization/applications', match: '/organization/applications' },
  { label: 'Statistics', icon: BarChart3, href: '/organization/statistics', match: '/organization/statistics' }
];

const OrganizationSidebar = ({ activePath = '', isCollapsed = false, onToggleCollapse }) => (
  <aside className={`hidden bg-[#2d2d2d] text-white lg:flex lg:flex-col transition-all duration-300 ${isCollapsed ? 'w-20' : 'w-72'}`}>
    <div className="flex h-14 items-center justify-between border-b border-white/10 px-5 text-sm">
      {!isCollapsed && <span>Collapse</span>}
      <button
        onClick={onToggleCollapse}
        className="rounded-lg p-1.5 hover:bg-white/10 transition-colors"
        aria-label="Toggle sidebar"
      >
        <X className="h-5 w-5" aria-hidden="true" />
      </button>
    </div>
    <nav className="space-y-1 flex-1 overflow-y-auto p-2" aria-label="Organization navigation">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = item.match && activePath.startsWith(item.match);
        const content = (
          <>
            <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            {!isCollapsed && (
              <>
                <span className="flex-1">{item.label}</span>
                <ChevronRight className="h-4 w-4 shrink-0" aria-hidden="true" />
              </>
            )}
          </>
        );
        const className = [
          'flex h-12 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors justify-start',
          item.prominent && !isActive ? 'bg-white text-neutral-900 hover:bg-neutral-100' : '',
          isActive ? 'bg-white/25 text-white' : '',
          !item.prominent && !isActive ? 'text-white/90 hover:bg-white/10' : '',
        ].join(' ');

        if (item.href) {
          return (
            <Link key={item.label} to={item.href} className={className} title={isCollapsed ? item.label : ''}>
              {content}
            </Link>
          );
        }

        return (
          <button key={item.label} type="button" className={`${className} w-full`} title={isCollapsed ? item.label : ''}>
            {content}
          </button>
        );
      })}
    </nav>
  </aside>
);

export default OrganizationSidebar;
