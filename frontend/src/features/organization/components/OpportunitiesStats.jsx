import { useLanguage } from '../../../i18n/LanguageContext.jsx';

const OpportunitiesStats = ({ total, active, applications }) => {
  const { t } = useLanguage();
  return (
    <div className="mb-4 grid gap-3 sm:grid-cols-3">
      <div className="rounded-lg border border-neutral-200 bg-white p-4">
        <p className="text-sm text-neutral-500">{t('organization.publishedJobs')}</p>
        <p className="mt-1 text-2xl font-semibold text-neutral-950">{total}</p>
      </div>
      <div className="rounded-lg border border-neutral-200 bg-white p-4">
        <p className="text-sm text-neutral-500">{t('organization.activeJobs')}</p>
        <p className="mt-1 text-2xl font-semibold text-neutral-950">{active}</p>
      </div>
      <div className="rounded-lg border border-neutral-200 bg-white p-4">
        <p className="text-sm text-neutral-500">{t('organization.applications')}</p>
        <p className="mt-1 text-2xl font-semibold text-neutral-950">{applications}</p>
      </div>
    </div>
  );
};

export default OpportunitiesStats;
