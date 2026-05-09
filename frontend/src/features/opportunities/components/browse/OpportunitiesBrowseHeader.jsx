import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';

const OpportunitiesBrowseHeader = ({ isUserAuthenticated }) => (
  <header className="border-b border-neutral-200 bg-white">
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="mb-3 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-700">
            <Sparkles className="h-4 w-4" />
            BidWise Opportunity Explorer
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
            Find multi-source opportunities that match you
          </h1>
          <p className="mt-2 max-w-2xl text-base leading-7 text-neutral-700">
            Browse jobs, internships, projects and funding opportunities aggregated from multiple
            sources or jump right in and create a free profile to find the opportunities that fit
            you best.
          </p>
        </div>

        {!isUserAuthenticated ? (
          <Button
            asChild
            size="lg"
            className="group w-full !bg-blue-600 !text-white shadow-lg shadow-blue-600/20 ring-1 ring-blue-500/20 hover:!bg-blue-700 hover:shadow-blue-600/30 sm:w-auto"
          >
            <Link to="/login">
              Get Personalized Matches
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
        ) : null}
      </div>
    </div>
  </header>
);

export default OpportunitiesBrowseHeader;
