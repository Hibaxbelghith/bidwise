const OpportunitiesStats = ({ total, active, applications }) => (
  <div className="mb-4 grid gap-3 sm:grid-cols-3">
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-sm text-neutral-500">Published jobs</p>
      <p className="mt-1 text-2xl font-semibold text-neutral-950">{total}</p>
    </div>
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-sm text-neutral-500">Active jobs</p>
      <p className="mt-1 text-2xl font-semibold text-neutral-950">{active}</p>
    </div>
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-sm text-neutral-500">Applications</p>
      <p className="mt-1 text-2xl font-semibold text-neutral-950">{applications}</p>
    </div>
  </div>
);

export default OpportunitiesStats;
