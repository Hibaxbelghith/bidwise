const toneStyles = {
  green: 'bg-green-500',
  blue: 'bg-blue-500',
  red: 'bg-red-500',
  yellow: 'bg-yellow-500',
  neutral: 'bg-neutral-400',
};

const Sparkline = ({ values, tone = 'blue', label = 'Trend' }) => {
  const numbers = Array.isArray(values)
    ? values.map((value) => Number(value || 0)).filter((value) => Number.isFinite(value))
    : [];
  const maxValue = Math.max(...numbers, 1);
  const barColor = toneStyles[tone] || toneStyles.blue;

  if (!numbers.length) {
    return (
      <div className="flex h-8 items-end gap-1" aria-label={`${label}: no data`}>
        {[0, 1, 2, 3, 4].map((index) => (
          <span key={index} className="w-1.5 rounded-full bg-neutral-200" style={{ height: `${8 + index * 2}px` }} />
        ))}
      </div>
    );
  }

  return (
    <div className="flex h-8 items-end gap-1" aria-label={`${label}: ${numbers.join(', ')}`}>
      {numbers.map((value, index) => (
        <span
          key={`${value}-${index}`}
          className={`w-1.5 rounded-full ${barColor}`}
          style={{ height: `${8 + (value / maxValue) * 22}px` }}
          title={`${label}: ${value}`}
        />
      ))}
    </div>
  );
};

export default Sparkline;
