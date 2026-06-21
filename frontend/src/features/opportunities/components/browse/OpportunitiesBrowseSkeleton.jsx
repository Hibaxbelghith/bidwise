export const SkeletonOpportunityCard = () => (
  <article className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <div className="space-y-4">
      <div className="flex items-start gap-4">
        <div className="h-12 w-12 shrink-0 rounded-xl bg-neutral-200" />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="h-4 w-3/4 rounded bg-neutral-200" />
          <div className="h-3 w-1/2 rounded bg-neutral-100" />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="h-3 w-24 rounded-full bg-neutral-100" />
        <div className="h-3 w-28 rounded-full bg-neutral-100" />
        <div className="h-3 w-20 rounded-full bg-neutral-100" />
      </div>

      <div className="space-y-2">
        <div className="h-3 w-full rounded bg-neutral-100" />
        <div className="h-3 w-11/12 rounded bg-neutral-100" />
        <div className="h-3 w-2/3 rounded bg-neutral-100" />
      </div>
    </div>
  </article>
);

export const FetchingSkeletonBanner = () => (
  <div className="mb-4 rounded-xl border border-neutral-200 bg-white px-4 py-3 shadow-sm">
    <div className="space-y-2">
      <div className="h-2 w-36 rounded-full bg-neutral-200" />
      <div className="h-2 w-full rounded-full bg-neutral-100" />
    </div>
  </div>
);

const OpportunitiesBrowseSkeleton = () => (
  <div className="space-y-4">
    {[0, 1, 2].map((index) => (
      <SkeletonOpportunityCard key={index} />
    ))}
  </div>
);

export default OpportunitiesBrowseSkeleton;
