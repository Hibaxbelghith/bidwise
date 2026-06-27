import { Badge } from '../../../../components/ui/badge.jsx';
import { statusStyles } from './dashboard.Utils.js';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const statusKeys = {
  success: 'admin.statusSuccess',
  failed: 'admin.statusFailed',
  skipped: 'admin.statusSkipped',
  running: 'admin.statusRunning',
  idle: 'admin.statusIdle',
  healthy: 'admin.statusHealthy',
  degraded: 'admin.statusDegraded',
};

const humanizeStatus = (status, t) => {
  const key = statusKeys[String(status || '').toLowerCase()];
  if (key) return t(key);
  return String(status || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || t('admin.unknown');
};

const StatusBadge = ({ status }) => {
  const { t } = useLanguage();
  return (
    <Badge variant="outline" className={statusStyles[status] || 'border-neutral-200 text-neutral-700'}>
      {humanizeStatus(status, t)}
    </Badge>
  );
};

export default StatusBadge;
