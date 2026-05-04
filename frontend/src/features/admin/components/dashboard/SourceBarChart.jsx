import { formatNumber } from './dashboard.Utils.js';

const EmptyChart = () => (
  <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-neutral-200 text-sm text-neutral-500">
    No data available
  </div>
);

const SourceBarChart = ({ data }) => {
  const maxCount = Math.max(...data.map((item) => item.count), 0);

  if (!data.length || maxCount === 0) return <EmptyChart />;

  return (
    <div className="space-y-4">
      {data.map((item) => {
        const width = `${Math.max((item.count / maxCount) * 100, 3)}%`;
        return (
          <div key={item.name} className="space-y-2">
            <div className="flex items-center justify-between gap-4 text-sm">
              <span className="truncate font-medium text-neutral-700">{item.name}</span>
              <span className="text-neutral-500">{formatNumber(item.count)}</span>
            </div>
            <div className="h-3 rounded-full bg-neutral-100">
              <div className="h-3 rounded-full bg-blue-600" style={{ width }} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default SourceBarChart;
