import {
  AlertTriangle,
  CheckCircle2,
  ClockAlert,
  Flame,
  Info,
  PauseCircle,
} from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';

const toneStyles = {
  green: 'border-green-200 bg-green-50 text-green-700',
  yellow: 'border-yellow-200 bg-yellow-50 text-yellow-800',
  red: 'border-red-200 bg-red-50 text-red-700',
  blue: 'border-blue-200 bg-blue-50 text-blue-700',
  neutral: 'border-neutral-200 bg-neutral-50 text-neutral-700',
};

const iconMap = {
  HIGH_VOLUME: Flame,
  COOLDOWN: PauseCircle,
  STALE: ClockAlert,
  FAILURE: AlertTriangle,
  STANDARD: CheckCircle2,
  NO_DATA: Info,
};

const StatusBadge = ({ badge }) => {
  const Icon = iconMap[badge?.type] || CheckCircle2;
  const tooltip = badge?.tooltip || '';

  return (
    <span className="group relative inline-flex" tabIndex={0} aria-label={`${badge?.label}: ${tooltip}`}>
      <Badge
        variant="outline"
        className={`gap-1.5 whitespace-nowrap ${toneStyles[badge?.tone] || toneStyles.neutral}`}
      >
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        {badge?.label}
      </Badge>
      {tooltip ? (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-48 -translate-x-1/2 rounded-md bg-neutral-900 px-2.5 py-2 text-center text-xs font-medium normal-case text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus:opacity-100"
        >
          {tooltip}
        </span>
      ) : null}
    </span>
  );
};

export default StatusBadge;
