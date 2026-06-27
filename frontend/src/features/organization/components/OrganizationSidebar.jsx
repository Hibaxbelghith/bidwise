import { Link } from 'react-router-dom';
import {
  BarChart3,
  BriefcaseBusiness,
  ChevronRight,
  Plus,
  Users,
  X,
} from 'lucide-react';
import { useLanguage } from '../../../i18n/LanguageContext.jsx';

const navItems = [
  { labelKey: 'organization.create', icon: Plus, href: '/organization/post', prominent: true, match: '/organization/post' },
  { labelKey: 'organization.jobs', icon: BriefcaseBusiness, href: '/organization/dashboard', match: '/organization/dashboard' },
  { labelKey: 'organization.applications', icon: Users, href: '/organization/applications', match: '/organization/applications' },
  { labelKey: 'organization.statistics', icon: BarChart3, href: '/organization/statistics', match: '/organization/statistics' }
];

const OrganizationSidebar = ({ activePath = '', isCollapsed = false, onToggleCollapse }) => {
  const { t } = useLanguage();
  return (
  <aside className={`hidden bg-[#2d2d2d] text-white lg:flex lg:flex-col transition-all duration-300 ${isCollapsed ? 'w-20' : 'w-72'}`}>
    <div className="flex h-14 items-center justify-between border-b border-white/10 px-5 text-sm">
      {!isCollapsed && <span>{t('organization.collapse')}</span>}
      <button
        onClick={onToggleCollapse}
        className="rounded-lg p-1.5 hover:bg-white/10 transition-colors"
        aria-label={t('organization.toggleSidebar')}
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
                <span className="flex-1">{t(item.labelKey)}</span>
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
            <Link key={item.labelKey} to={item.href} className={className} title={isCollapsed ? t(item.labelKey) : ''}>
              {content}
            </Link>
          );
        }

        return (
          <button key={item.labelKey} type="button" className={`${className} w-full`} title={isCollapsed ? t(item.labelKey) : ''}>
            {content}
          </button>
        );
      })}
    </nav>
  </aside>
  );
};

export default OrganizationSidebar;
