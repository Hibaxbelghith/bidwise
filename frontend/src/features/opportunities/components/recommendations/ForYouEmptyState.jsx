import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { getProfileActionItems } from '../../utils/recommendationUtils.js';

const ForYouEmptyState = ({
  user,
  isUserAuthenticated,
  hasActiveFilters,
  onResetFilters,
  title = 'We need more information to personalize your recommendations.',
  description = 'Add a few profile signals and BidWise AI can rank opportunities around your skills, preferred roles, and resume evidence.',
}) => {
  const actions = isUserAuthenticated
    ? getProfileActionItems(user)
    : ['Create Profile', 'Add Skills', 'Upload Resume'];

  return (
    <section className="rounded-md border border-neutral-200 bg-white p-6 text-center shadow-sm sm:p-8">
      <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-md bg-blue-50 text-blue-700">
        <Sparkles className="h-6 w-6" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-xl font-semibold text-neutral-950">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-neutral-600">{description}</p>

      <div className="mt-5 flex flex-wrap justify-center gap-2">
        {actions.slice(0, 3).map((action) => (
          <span
            key={action}
            className="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-semibold text-neutral-700"
          >
            {action}
          </span>
        ))}
      </div>

      <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
        <Button asChild className="bg-blue-600 text-white hover:bg-blue-700">
          <Link to={isUserAuthenticated ? '/profile' : '/login'}>
            {isUserAuthenticated ? actions[0] : 'Create profile'}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </Button>
        {hasActiveFilters ? (
          <Button type="button" variant="outline" onClick={onResetFilters}>
            Clear Explore filters
          </Button>
        ) : null}
      </div>
    </section>
  );
};

export default ForYouEmptyState;
