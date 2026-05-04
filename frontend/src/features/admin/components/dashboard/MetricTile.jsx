const toneClasses = {
  blue: 'border-blue-200 bg-blue-50 text-blue-800',
  green: 'border-green-200 bg-green-50 text-green-800',
  yellow: 'border-yellow-200 bg-yellow-50 text-yellow-800',
  red: 'border-red-200 bg-red-50 text-red-800',
  neutral: 'border-neutral-200 bg-white text-neutral-900',
};

const MetricTile = ({ label, value, detail, tone = 'neutral' }) => (
  <div className={`rounded-lg border p-4 ${toneClasses[tone] || toneClasses.neutral}`}>
    <p className="text-xs font-medium uppercase opacity-75">{label}</p>
    <p className="mt-2 text-xl font-bold">{value}</p>
    {detail ? <p className="mt-1 text-xs opacity-75">{detail}</p> : null}
  </div>
);

export default MetricTile;
