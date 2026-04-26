const KeyInfoCard = ({ icon, label, value }) => {
  if (!value) return null;

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white px-4 py-3 shadow-sm">
      <p className="mb-1 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        {icon}
        {label}
      </p>
      <p className="text-sm font-medium text-neutral-900">{value}</p>
    </div>
  );
};

export default KeyInfoCard;
