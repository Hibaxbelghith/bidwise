import { ChevronDown, ChevronUp } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import { DESCRIPTION_COLLAPSE_HEIGHT } from '../../constants/opportunityDetail.js';

const OpportunityDescriptionSection = ({
  descriptionMarkup,
  isLongDescription,
  isDescriptionExpanded,
  onToggleDescription,
}) => {
  const { t } = useLanguage();

  return (
  <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="text-lg font-semibold text-neutral-900">{t('opportunities.detail.description')}</h2>
      {isLongDescription ? (
        <Button variant="ghost" size="sm" onClick={onToggleDescription}>
          {isDescriptionExpanded ? (
            <>
              {t('opportunities.detail.showLess')} <ChevronUp className="h-4 w-4" />
            </>
          ) : (
            <>
              {t('opportunities.detail.showMore')} <ChevronDown className="h-4 w-4" />
            </>
          )}
        </Button>
      ) : null}
    </div>

    <div
      className="relative rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3"
      style={
        isDescriptionExpanded || !isLongDescription
          ? undefined
          : { maxHeight: DESCRIPTION_COLLAPSE_HEIGHT, overflow: 'hidden' }
      }
    >
      <div
        className="whitespace-pre-wrap text-sm leading-7 text-neutral-700"
        dangerouslySetInnerHTML={{ __html: descriptionMarkup }}
      />

      {!isDescriptionExpanded && isLongDescription ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-neutral-50 to-transparent" />
      ) : null}
    </div>
  </section>
  );
};

export default OpportunityDescriptionSection;
