import { useMemo } from 'react';

import OpportunityCard from './OpportunityCard.jsx';
import { dedupeSimilarOpportunities } from './utils/similarity.js';

const SimilarOpportunitiesLoading = () => (
  <div className="space-y-3">
    <p className="text-neutral-600">Finding similar opportunities...</p>
    <div className="h-16 animate-pulse rounded-md border border-neutral-200 bg-neutral-100" />
    <div className="h-16 animate-pulse rounded-md border border-neutral-200 bg-neutral-100" />
  </div>
);

const SimilarOpportunities = ({ opportunities = [], loading = false }) => {
  const dedupedItems = useMemo(
    () => dedupeSimilarOpportunities(opportunities).slice(0, 5),
    [opportunities]
  );

  if (loading) {
    return <SimilarOpportunitiesLoading />;
  }

  if (!dedupedItems.length) {
    return <p className="text-neutral-600">No similar opportunities found</p>;
  }

  return (
    <div className="space-y-3">
      {dedupedItems.map((item) => (
        <OpportunityCard
          key={item?.id ?? `${item?.titre || 'untitled'}-fallback`}
          opportunity={item}
        />
      ))}
    </div>
  );
};

export default SimilarOpportunities;
