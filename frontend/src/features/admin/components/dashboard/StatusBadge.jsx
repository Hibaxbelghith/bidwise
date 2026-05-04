import { Badge } from '../../../../components/ui/badge.jsx';
import { statusStyles } from './dashboard.Utils.js';

const StatusBadge = ({ status }) => (
  <Badge variant="outline" className={statusStyles[status] || 'border-neutral-200 text-neutral-700'}>
    {status}
  </Badge>
);

export default StatusBadge;
