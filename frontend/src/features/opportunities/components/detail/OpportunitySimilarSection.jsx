import { Link } from 'react-router-dom';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import LockPreviewCard from './LockPreviewCard.jsx';
import SimilarOpportunityCard from './SimilarOpportunityCard.jsx';

const OpportunitySimilarSection = ({
  isUserAuthenticated,
  similarOpportunities,
  loading,
  error,
}) => (
  <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="text-lg font-semibold text-neutral-900">Similar opportunities</h2>
      <Badge variant="outline">{isUserAuthenticated ? 'Available' : 'Locked preview'}</Badge>
    </div>

    {isUserAuthenticated ? (
      <>
        {loading ? (
          <div className="space-y-3">
            <div className="h-16 animate-pulse rounded-2xl border border-neutral-200 bg-neutral-100" />
            <div className="h-16 animate-pulse rounded-2xl border border-neutral-200 bg-neutral-100" />
          </div>
        ) : null}

        {!loading && error ? (
          <p className="text-sm text-neutral-600">
            Similar opportunities are currently unavailable. Please retry later.
          </p>
        ) : null}

        {!loading && !error && !similarOpportunities.length ? (
          <p className="text-sm text-neutral-600">No similar opportunities found.</p>
        ) : null}

        {!loading && !error && similarOpportunities.length ? (
          <div className="space-y-3">
            {similarOpportunities.map((opportunity) => (
              <SimilarOpportunityCard key={opportunity.id} opportunity={opportunity} />
            ))}
          </div>
        ) : null}
      </>
    ) : (
      <>
        <div className="space-y-3">
          <LockPreviewCard
            title="Ranked recommendations"
            body="Get a personalized ranking of similar opportunities based on your profile."
          />
          <LockPreviewCard
            title="One-click comparison"
            body="Compare opportunities side by side to pick the strongest applications."
          />
          <LockPreviewCard
            title="Continuous discovery"
            body="Receive fresh similar opportunities as new listings are indexed."
          />
        </div>

        <Button asChild className="mt-4 w-full sm:w-auto" variant="outline">
          <Link to="/login">Login to view similar opportunities</Link>
        </Button>
      </>
    )}
  </section>
);

export default OpportunitySimilarSection;
