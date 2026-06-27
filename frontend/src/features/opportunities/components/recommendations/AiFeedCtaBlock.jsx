import { ArrowRight, Compass, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const AiFeedCtaBlock = ({ onExploreMore }) => {
  const { t } = useLanguage();

  return (
  <section className="rounded-md border border-neutral-200 bg-white p-5 shadow-sm">
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="min-w-0">
        <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase text-blue-700">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          {t('opportunities.curatedByAi')}
        </p>
        <h2 className="mt-1 text-lg font-semibold text-neutral-950">
          {t('opportunities.exploreMoreTitle')}
        </h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-neutral-600">
          {t('opportunities.exploreMoreDesc')}
        </p>
      </div>

      <Button
        type="button"
        className="shrink-0 bg-neutral-950 text-white hover:bg-neutral-800"
        onClick={onExploreMore}
      >
        <Compass className="h-4 w-4" aria-hidden="true" />
        {t('opportunities.exploreMoreTitle')}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    </div>
  </section>
  );
};

export default AiFeedCtaBlock;
