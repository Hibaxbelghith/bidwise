import { Link } from 'react-router-dom';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import LockPreviewCard from './LockPreviewCard.jsx';
import SimilarOpportunityCard from './SimilarOpportunityCard.jsx';

const OpportunitySimilarSection = ({
  isUserAuthenticated,
  similarOpportunities,
  loading,
  error,
}) => {
  const { t } = useLanguage();

  return (
  <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="text-lg font-semibold text-neutral-900">{t('opportunities.detail.similarOpportunities')}</h2>
      <Badge variant="outline">{isUserAuthenticated ? t('opportunities.detail.available') : t('opportunities.detail.lockedPreview')}</Badge>
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
            {t('opportunities.detail.similarUnavailable')}
          </p>
        ) : null}

        {!loading && !error && !similarOpportunities.length ? (
          <p className="text-sm text-neutral-600">{t('opportunities.detail.noSimilarFound')}</p>
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
            title={t('opportunities.detail.rankedRecommendations')}
            body={t('opportunities.detail.rankedRecommendationsBody')}
          />
          <LockPreviewCard
            title={t('opportunities.detail.oneClickComparison')}
            body={t('opportunities.detail.oneClickComparisonBody')}
          />
          <LockPreviewCard
            title={t('opportunities.detail.continuousDiscovery')}
            body={t('opportunities.detail.continuousDiscoveryBody')}
          />
        </div>

        <Button asChild className="mt-4 w-full sm:w-auto" variant="outline">
          <Link to="/login">{t('opportunities.detail.loginSimilar')}</Link>
        </Button>
      </>
    )}
  </section>
  );
};

export default OpportunitySimilarSection;
