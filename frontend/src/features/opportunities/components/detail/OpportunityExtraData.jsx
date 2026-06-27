import {
  Briefcase,
  Building2,
  Calendar,
  MapPin,
  Wallet,
} from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import KeyInfoCard from './KeyInfoCard.jsx';

const OpportunityExtraData = ({
  isProject,
  additionalInfoItems,
  organizationLabel,
  publishedDateLabel,
  deadlineDateLabel,
  projectRegionLabel,
  projectProcedureLabel,
  projectFinancementLabel,
  projectTypeCommandeLabel,
  projectDelaiValiditeLabel,
  projectCautionLabel,
  projectLots,
}) => {
  const { t } = useLanguage();

  return (
    <>
      {additionalInfoItems.length ? (
        <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-neutral-900">{t('opportunities.detail.additionalInfo')}</h2>
          <dl className="grid gap-3 md:grid-cols-2">
            {additionalInfoItems.map((item) => (
              <div key={item.label} className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  {item.label}
                </dt>
                <dd className="mt-1 whitespace-pre-wrap text-sm leading-6 text-neutral-800">
                  {item.value}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}

      {isProject ? (
        <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-neutral-900">{t('opportunities.detail.tenderDetails')}</h2>
            {projectLots.length ? (
              <Badge variant="outline">
                {projectLots.length} {t(projectLots.length > 1 ? 'opportunities.card.lots' : 'opportunities.card.lot')}
              </Badge>
            ) : null}
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <KeyInfoCard icon={<Building2 className="h-3.5 w-3.5" />} label={t('opportunities.detail.buyer')} value={organizationLabel} />
            <KeyInfoCard icon={<MapPin className="h-3.5 w-3.5" />} label={t('opportunities.detail.region')} value={projectRegionLabel} />
            <KeyInfoCard
              icon={<Calendar className="h-3.5 w-3.5" />}
              label={t('opportunities.detail.publicationDate')}
              value={publishedDateLabel}
            />
            <KeyInfoCard
              icon={<Calendar className="h-3.5 w-3.5" />}
              label={t('opportunities.detail.deadline')}
              value={deadlineDateLabel}
            />
            <KeyInfoCard
              icon={<Briefcase className="h-3.5 w-3.5" />}
              label={t('opportunities.detail.procedure')}
              value={projectProcedureLabel}
            />
            <KeyInfoCard
              icon={<Wallet className="h-3.5 w-3.5" />}
              label={t('opportunities.detail.financing')}
              value={projectFinancementLabel}
            />
            <KeyInfoCard
              icon={<Briefcase className="h-3.5 w-3.5" />}
              label={t('opportunities.detail.orderType')}
              value={projectTypeCommandeLabel}
            />
            <KeyInfoCard
              icon={<Calendar className="h-3.5 w-3.5" />}
              label={t('opportunities.detail.offerValidity')}
              value={projectDelaiValiditeLabel}
            />
            <KeyInfoCard icon={<Wallet className="h-3.5 w-3.5" />} label={t('opportunities.card.caution')} value={projectCautionLabel} />
          </div>

          {projectLots.length ? (
            <div className="mt-5">
              <h3 className="mb-3 text-base font-semibold text-neutral-900">{t('opportunities.detail.lots')}</h3>
              <div className="grid gap-3 md:grid-cols-2">
                {projectLots.map((lot, index) => (
                  <div
                    key={`${lot?.lot || 'lot'}-${index}`}
                    className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4"
                  >
                    <p className="text-sm font-semibold text-neutral-900">{lot?.lot || `Lot ${index + 1}`}</p>
                    {lot?.objet ? <p className="mt-2 text-sm text-neutral-700">{lot.objet}</p> : null}
                    <div className="mt-3 space-y-2 text-xs text-neutral-600">
                      {lot?.quantite ? <p>{t('opportunities.detail.quantity')}: {lot.quantite}</p> : null}
                      {lot?.region ? <p>{t('opportunities.detail.region')}: {lot.region}</p> : null}
                      {lot?.caution ? <p>{t('opportunities.card.caution')}: {lot.caution}</p> : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </>
  );
};

export default OpportunityExtraData;
