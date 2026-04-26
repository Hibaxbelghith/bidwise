const OpportunityDetailSkeleton = () => (
  <div className="min-h-screen bg-neutral-50 pb-28">
    <div className="border-b border-neutral-200 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-44 rounded bg-neutral-200" />
          <div className="h-8 w-2/3 rounded bg-neutral-200" />
          <div className="h-4 w-1/2 rounded bg-neutral-100" />
        </div>
      </div>
    </div>

    <div className="mx-auto max-w-6xl space-y-5 px-4 py-6 sm:px-6 lg:px-8">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="h-20 animate-pulse rounded-2xl border border-neutral-200 bg-white" />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
          <div className="h-64 animate-pulse rounded-2xl border border-neutral-200 bg-white" />
          <div className="h-56 animate-pulse rounded-2xl border border-neutral-200 bg-white" />
          <div className="h-56 animate-pulse rounded-2xl border border-neutral-200 bg-white" />
        </div>
        <div className="h-72 animate-pulse rounded-2xl border border-neutral-200 bg-white" />
      </div>
    </div>
  </div>
);

export default OpportunityDetailSkeleton;
