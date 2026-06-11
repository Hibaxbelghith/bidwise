import { Badge } from '../../../../components/ui/badge.jsx';
import { statusStyles } from './dashboard.Utils.js';

const humanizeStatus = (status) =>
  String(status || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown';

const StatusBadge = ({ status }) => (
  <Badge variant="outline" className={statusStyles[status] || 'border-neutral-200 text-neutral-700'}>
    {humanizeStatus(status)}
  </Badge>
);

export default StatusBadge;
