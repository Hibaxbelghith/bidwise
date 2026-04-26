import { Link } from 'react-router-dom';
import { Lock, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';

const GuestLockPanel = () => (
  <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4 shadow-sm">
    <p className="mb-3 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-blue-700">
      <Lock className="h-4 w-4" />
      Guest mode
    </p>
    <h2 className="text-base font-semibold text-blue-900">Core data is open, AI intelligence is locked</h2>
    <p className="mt-2 text-sm leading-6 text-blue-900/90">
      Browse title, company, location, salary, skills and descriptions. Login to unlock match
      score, recommendations, and action shortcuts.
    </p>
    <Button asChild className="mt-4 w-full sm:w-auto">
      <Link to="/login">Login to unlock</Link>
    </Button>
  </div>
);

const AuthValuePanel = () => (
  <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
    <p className="mb-3 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-emerald-700">
      <Sparkles className="h-4 w-4" />
      Signed in
    </p>
    <h2 className="text-base font-semibold text-emerald-900">AI insights are available on each opportunity</h2>
    <p className="mt-2 text-sm leading-6 text-emerald-900/90">
      Open any detail page to access match score, explainability insights, and action workflow.
    </p>
  </div>
);

const OpportunitiesBrowseHeader = ({ isUserAuthenticated }) => (
  <header className="border-b border-neutral-200 bg-white">
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_390px]">
        <div>
          <p className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            <Sparkles className="h-4 w-4" />
            BidWise Opportunity Explorer
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900">Browse Opportunities</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
            Discover jobs, internships, projects, and funding opportunities with a clean,
            focused workflow.
          </p>
        </div>

        {isUserAuthenticated ? <AuthValuePanel /> : <GuestLockPanel />}
      </div>
    </div>
  </header>
);

export default OpportunitiesBrowseHeader;
