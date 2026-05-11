import { ArrowRight, Compass, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';

const AiFeedCtaBlock = ({ onExploreMore }) => (
  <section className="rounded-md border border-neutral-200 bg-white p-5 shadow-sm">
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="min-w-0">
        <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase text-blue-700">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Curated by BidWise AI
        </p>
        <h2 className="mt-1 text-lg font-semibold text-neutral-950">
          Explore more opportunities
        </h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-neutral-600">
          Browse the full multi-source index with filters, facets, and lightweight match badges.
        </p>
      </div>

      <Button
        type="button"
        className="shrink-0 bg-neutral-950 text-white hover:bg-neutral-800"
        onClick={onExploreMore}
      >
        <Compass className="h-4 w-4" aria-hidden="true" />
        Explore more opportunities
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    </div>
  </section>
);

export default AiFeedCtaBlock;
