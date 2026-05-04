import { Badge } from '../../../../components/ui/badge.jsx';
import { severityStyles } from './dashboard.Utils.js';

const AlertList = ({ alerts }) => {
  if (!alerts.length) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-800">
        No active pipeline alerts.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div key={alert.issue_key} className="rounded-lg border border-neutral-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="outline" className={severityStyles[alert.severity] || severityStyles.INFO}>
              {alert.severity}
            </Badge>
            {alert.source ? <span className="text-sm font-semibold text-neutral-900">{alert.source}</span> : null}
          </div>
          <p className="mt-2 font-medium text-neutral-900">{alert.title}</p>
          {alert.details ? <p className="mt-1 text-sm text-neutral-600">{alert.details}</p> : null}
        </div>
      ))}
    </div>
  );
};

export default AlertList;
