import { Link } from 'react-router-dom';
import { ArrowRight, FileText, SearchCheck, Sparkles, UserCheck, Zap } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import OpportunitiesBrowseSkeleton, {
  FetchingSkeletonBanner,
} from './OpportunitiesBrowseSkeleton.jsx';
import OpportunityBrowseCard from './OpportunityBrowseCard.jsx';
import {
  getProfileCompletionScore,
  hasActiveResume,
} from '../../utils/recommendationUtils.js';

const normalizeProfileStrength = (user) => {
  const explicitStrength = String(user?.profil?.profile_strength || '').trim().toUpperCase();
  if (explicitStrength) return explicitStrength;

  const completionScore = getProfileCompletionScore(user);
  if (completionScore >= 80) return 'HIGH';
  if (completionScore >= 60) return 'MEDIUM';
  return 'LOW';
};

const getProfileStatus = (user) => {
  const profile = user?.profil || {};
  const skills = Array.isArray(profile.competences) ? profile.competences : [];
  const targetRoles = Array.isArray(profile.target_roles) ? profile.target_roles : [];
  const profileStrength = normalizeProfileStrength(user);

  return {
    profileStrength,
    hasResume: hasActiveResume(user),
    hasMissingSkills: skills.length === 0,
    hasMissingTargetRoles: targetRoles.length === 0,
    onboardingIncomplete: !profile.onboarding_completed,
  };
};

const buildInterruptionCards = ({ isUserAuthenticated, user, onShowMatches }) => {
  if (!isUserAuthenticated) {
    return [
      {
        key: 'guest',
        icon: Sparkles,
        eyebrow: 'Personalized matching',
        title: 'Find opportunities that actually match you.',
        description:
          'Create a free profile to unlock AI-powered recommendations and personalized opportunity matching.',
        ctaLabel: 'Get Personalized Matches',
        to: '/login',
        accentClassName: 'bg-blue-50 text-blue-700',
      },
    ];
  }

  const status = getProfileStatus(user);
  const cards = [];

  if (!status.hasResume) {
    cards.push({
      key: 'resume',
      icon: FileText,
      eyebrow: 'Resume intelligence',
      title: 'Upload your resume to improve recommendation accuracy.',
      description:
        'BidWise AI can analyze your resume and deliver stronger personalized matches.',
      ctaLabel: 'Upload Resume',
      to: '/profile',
      accentClassName: 'bg-emerald-50 text-emerald-700',
    });
  }

  if (
    status.profileStrength === 'LOW' ||
    status.hasMissingSkills ||
    status.hasMissingTargetRoles ||
    status.onboardingIncomplete
  ) {
    cards.push({
      key: 'profile',
      icon: UserCheck,
      eyebrow: 'Profile strength',
      title: 'Your profile is incomplete.',
      description: 'Add skills and target roles to unlock more relevant opportunities.',
      ctaLabel: 'Complete Profile',
      to: '/profile',
      accentClassName: 'bg-amber-50 text-amber-700',
    });
  }

  if (
    ['MEDIUM', 'HIGH'].includes(status.profileStrength) &&
    status.hasResume &&
    typeof onShowMatches === 'function'
  ) {
    cards.push({
      key: 'matches',
      icon: SearchCheck,
      eyebrow: 'For You feed',
      title: 'Search smarter, not harder.',
      description: 'Get a personalized list of opportunities matched to your profile.',
      ctaLabel: 'See Your Matches',
      onClick: onShowMatches,
      accentClassName: 'bg-blue-50 text-blue-700',
    });
  }

  return cards;
};

const ScrollInterruptionCard = ({ card }) => {
  const Icon = card.icon;
  
  const colorMap = {
    blue: 'from-blue-600 to-indigo-500',
    purple: 'from-purple-600 to-violet-500',
    emerald: 'from-emerald-600 to-teal-500',
    amber: 'from-amber-600 to-orange-500',
    rose: 'from-rose-600 to-pink-500'
  };
  
  const gradient = colorMap[card.color] || colorMap.blue;
  const lightGradient = gradient.replace('600', '50').replace('500', '100');
  
  const ctaClassName = `group relative overflow-hidden rounded-xl bg-gradient-to-r ${gradient} px-6 py-2.5 text-sm font-medium text-white shadow-lg shadow-${card.color || 'blue'}-500/20 transition-all duration-300 hover:shadow-xl hover:shadow-${card.color || 'blue'}-500/30 hover:scale-[1.02] active:scale-[0.98] sm:w-auto`;

  return (
    <article className="group relative overflow-hidden rounded-2xl bg-white border border-neutral-200/80 shadow-lg transition-all duration-500 hover:shadow-2xl hover:border-neutral-300/100">
      
      {/* Animated gradient background */}
      <div className={`absolute inset-0 bg-gradient-to-br ${lightGradient} opacity-0 transition-opacity duration-500 group-hover:opacity-100`} />
      
      {/* Glow effect */}
      <div className={`absolute -inset-1 bg-gradient-to-r ${gradient} opacity-0 blur-xl transition-all duration-500 group-hover:opacity-20`} />
      
      {/* Décorations */}
      <div className={`absolute -right-16 -top-16 h-32 w-32 rounded-full bg-${card.color || 'blue'}-500/5 transition-all duration-700 group-hover:scale-150 group-hover:bg-${card.color || 'blue'}-500/10`} />
      <div className={`absolute -bottom-16 -left-16 h-32 w-32 rounded-full bg-${card.color || 'blue'}-500/5 transition-all duration-700 delay-100 group-hover:scale-150 group-hover:bg-${card.color || 'blue'}-500/10`} />

      <div className="relative p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          
          <div className="flex min-w-0 flex-1 gap-4">
            {/* Icône 3D */}
            <div className="relative">
              <div className={`absolute -inset-1 rounded-2xl bg-gradient-to-r ${gradient} opacity-0 blur-lg transition-all duration-500 group-hover:opacity-30`} />
              <div className={`relative flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${lightGradient} transition-all duration-300 group-hover:scale-110`}>
                <Icon className={`h-5 w-5 text-${card.color || 'blue'}-600`} aria-hidden="true" />
              </div>
            </div>
            
            <div className="min-w-0 flex-1">
              {/* Badge */}

              
              <h2 className="text-lg font-bold leading-tight text-neutral-900 lg:text-xl">
                {card.title}
                {card.isNew && (
                  <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                    <Sparkles className="h-2.5 w-2.5" />
                    New
                  </span>
                )}
              </h2>
              
              <p className="mt-1 text-sm leading-relaxed text-neutral-500">
                {card.description}
              </p>
            </div>
          </div>

          {/* CTA */}
          <div className="flex shrink-0">
            {card.to ? (
              <Button asChild className={ctaClassName}>
                <Link to={card.to}>
                  {card.ctaLabel}
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                </Link>
              </Button>
            ) : (
              <Button type="button" className={ctaClassName} onClick={card.onClick}>
                {card.ctaLabel}
                <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </Button>
            )}
          </div>
        </div>
      </div>

</article>
  );
};

const OpportunitiesBrowseResults = ({
  resultsSectionRef,
  countLabel,
  page,
  totalPages,
  showFetchingSpinner,
  loading,
  isFetching,
  error,
  opportunities,
  isUserAuthenticated,
  user,
  hasPrevious,
  hasNext,
  visiblePageNumbers,
  onPageChange,
  onPreviousPage,
  onNextPage,
  onResetFilters,
  onRetry,
  onShowMatches,
}) => {
  const interruptionCards = buildInterruptionCards({
    isUserAuthenticated,
    user,
    onShowMatches,
  });

  return (
    <section ref={resultsSectionRef} className="min-w-0">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-neutral-700">{countLabel}</p>
        <p className="text-sm text-neutral-600">
          Page {page} of {totalPages}
        </p>
      </div>

      {showFetchingSpinner && opportunities.length > 0 ? <FetchingSkeletonBanner /> : null}

      {loading && opportunities.length === 0 ? <OpportunitiesBrowseSkeleton /> : null}

      {!loading && error && opportunities.length === 0 ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="mb-3">{error}</p>
          <Button variant="outline" onClick={onRetry}>
            Retry
          </Button>
        </div>
      ) : null}

      {!loading && error && opportunities.length > 0 ? (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {error}
        </div>
      ) : null}

      {!loading && !error && opportunities.length === 0 ? (
        <div className="rounded-xl border border-neutral-200 bg-white p-8 text-center shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-neutral-900">No opportunities found</h2>
          <p className="text-neutral-600">Try adjusting search terms or filters.</p>
          <div className="mt-4">
            <Button variant="outline" onClick={onResetFilters}>
              Reset filters
            </Button>
          </div>
        </div>
      ) : null}

      {!loading && opportunities.length > 0 ? (
        <div className="space-y-4">
          {opportunities.map((opportunity, index) => (
            <div key={opportunity.id || index} className="space-y-4">
              <OpportunityBrowseCard
                opportunity={opportunity}
                isUserAuthenticated={isUserAuthenticated}
              />
              {(index + 1) % 5 === 0 && interruptionCards.length > 0 ? (
                <ScrollInterruptionCard
                  card={interruptionCards[Math.floor(index / 5) % interruptionCards.length]}
                />
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
        <Button
          variant="outline"
          onClick={onPreviousPage}
          disabled={!hasPrevious || loading || isFetching}
        >
          Previous
        </Button>
        {visiblePageNumbers[0] > 1 ? (
          <>
            <Button
              type="button"
              variant={page === 1 ? 'default' : 'outline'}
              className="min-w-10"
              disabled={loading || isFetching}
              aria-current={page === 1 ? 'page' : undefined}
              onClick={() => onPageChange(1)}
            >
              1
            </Button>
            {visiblePageNumbers[0] > 2 ? (
              <span className="px-1 text-sm text-neutral-400" aria-hidden="true">
                ...
              </span>
            ) : null}
          </>
        ) : null}
        {visiblePageNumbers.map((pageNumber) => (
          <Button
            key={pageNumber}
            type="button"
            variant={pageNumber === page ? 'default' : 'outline'}
            className="min-w-10"
            disabled={loading || isFetching}
            aria-current={pageNumber === page ? 'page' : undefined}
            onClick={() => onPageChange(pageNumber)}
          >
            {pageNumber}
          </Button>
        ))}
        {visiblePageNumbers[visiblePageNumbers.length - 1] < totalPages ? (
          <>
            {visiblePageNumbers[visiblePageNumbers.length - 1] < totalPages - 1 ? (
              <span className="px-1 text-sm text-neutral-400" aria-hidden="true">
                ...
              </span>
            ) : null}
            <Button
              type="button"
              variant={page === totalPages ? 'default' : 'outline'}
              className="min-w-10"
              disabled={loading || isFetching}
              aria-current={page === totalPages ? 'page' : undefined}
              onClick={() => onPageChange(totalPages)}
            >
              {totalPages}
            </Button>
          </>
        ) : null}
        <Button
          variant="outline"
          onClick={onNextPage}
          disabled={!hasNext || loading || isFetching}
        >
          Next
        </Button>
      </div>
    </section>
  );
};

export default OpportunitiesBrowseResults;
