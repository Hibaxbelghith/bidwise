import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import { getRecommendationImprovementHints } from '../../utils/recommendationUtils.js';

const ForYouEmptyState = ({
  user,
  isUserAuthenticated,
  hasActiveFilters,
  onResetFilters,
  title,
  description,
}) => {
  const { t } = useLanguage();
  const hints = isUserAuthenticated ? getRecommendationImprovementHints(user) : [];
  const primaryHint = hints[0];
  const resolvedTitle = title || t('opportunities.needMoreInfo');
  const resolvedDescription = description || t('opportunities.needMoreInfoDesc');

  return (
    <section className="rounded-md border border-neutral-200 bg-white p-6 text-center shadow-sm sm:p-8">
      <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-md bg-blue-50 text-blue-700">
        <Sparkles className="h-6 w-6" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-xl font-semibold text-neutral-950">{resolvedTitle}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-neutral-600">{resolvedDescription}</p>

      {isUserAuthenticated ? (
        <div className="mt-5 grid gap-3 text-left sm:grid-cols-2">
          {hints.map((hint) => (
            <div
              key={hint.type}
              className="rounded-md border border-neutral-200 bg-neutral-50 p-4"
            >
              <p className="text-sm font-semibold text-neutral-900">{hint.title}</p>
              <p className="mt-1 text-sm leading-6 text-neutral-600">{hint.message}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {[t('opportunities.createProfileChip'), t('opportunities.addPreferences'), t('opportunities.uploadResume')].map((action) => (
            <span
              key={action}
              className="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-semibold text-neutral-700"
            >
              {action}
            </span>
          ))}
        </div>
      )}

      <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
        <Button asChild className="bg-blue-600 text-white hover:bg-blue-700">
          <Link to={isUserAuthenticated ? '/profile' : '/login'}>
            {isUserAuthenticated ? primaryHint?.ctaLabel || t('opportunities.reviewProfile') : t('opportunities.createProfile')}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </Button>
        {hasActiveFilters ? (
          <Button type="button" variant="outline" onClick={onResetFilters}>
            {t('opportunities.clearExploreFilters')}
          </Button>
        ) : null}
      </div>
    </section>
  );
};

export default ForYouEmptyState;
