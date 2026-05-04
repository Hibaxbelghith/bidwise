import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import StatusBadge from './StatusBadge.jsx';
import { formatDateTime, formatNumber } from './dashboard.Utils.js';

const PipelineHealthPanel = ({ pipeline }) => (
  <Card>
    <CardHeader>
      <CardTitle>Pipeline Health</CardTitle>
      <CardDescription>Current pipeline and Celery worker state.</CardDescription>
    </CardHeader>
    <CardContent className="space-y-5">
      <div className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-4">
        <div>
          <p className="text-sm font-medium text-neutral-600">Pipeline status</p>
          <p className="mt-1 text-2xl font-bold text-neutral-900">{formatNumber(pipeline?.processed ?? 0)}</p>
          <p className="text-xs text-neutral-500">Processed in last known run</p>
        </div>
        <StatusBadge status={pipeline?.status || 'idle'} />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <p className="text-xs font-medium uppercase text-neutral-500">Created</p>
          <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(pipeline?.created ?? 0)}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <p className="text-xs font-medium uppercase text-neutral-500">Updated</p>
          <p className="mt-2 text-xl font-bold text-neutral-900">{formatNumber(pipeline?.updated ?? 0)}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <p className="text-xs font-medium uppercase text-neutral-500">Last run</p>
          <p className="mt-2 text-sm font-semibold text-neutral-900">{formatDateTime(pipeline?.last_run)}</p>
        </div>
      </div>
    </CardContent>
  </Card>
);

export default PipelineHealthPanel;
