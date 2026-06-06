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
  { label: 'Smart sourcing', icon: Search },
  { label: 'Applications', icon: Users },
  { label: 'Interviews', icon: CalendarDays },
  { label: 'Analytics', icon: BarChart3 },
  { label: 'Tools', icon: Folder },
];

const OrganizationSidebar = ({ activePath = '' }) => (
  <aside className="hidden bg-[#2d2d2d] text-white lg:block">
    <div className="flex h-14 items-center gap-3 border-b border-white/10 px-5 text-sm">
      <X className="h-5 w-5" aria-hidden="true" />
      <span>Collapse</span>
    </div>
    <nav className="space-y-1 p-2" aria-label="Organization navigation">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = item.match && activePath.startsWith(item.match);
        const content = (
          <>
            <Icon className="h-5 w-5" aria-hidden="true" />
            <span className="flex-1">{item.label}</span>
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </>
        );
        const className = [
          'flex h-12 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors',
          item.prominent && !isActive ? 'bg-white text-neutral-900 hover:bg-neutral-100' : '',
          isActive ? 'bg-white/25 text-white' : '',
          !item.prominent && !isActive ? 'text-white/90 hover:bg-white/10' : '',
        ].join(' ');

        if (item.href) {
          return (
            <Link key={item.label} to={item.href} className={className}>
              {content}
            </Link>
          );
        }

        return (
          <button key={item.label} type="button" className={`${className} w-full text-left`}>
            {content}
          </button>
        );
      })}
    </nav>
  </aside>
);

export default OrganizationSidebar;
