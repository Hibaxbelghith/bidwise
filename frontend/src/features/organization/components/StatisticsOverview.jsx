import { useLanguage } from '../../../i18n/LanguageContext.jsx';

const StatisticsOverview = ({ stats }) => {
  const { t } = useLanguage();
  const cards = [
    {
      label: t('organization.publishedOpportunities'),
      value: stats.totalOpportunities,
    },
    {
      label: t('organization.activeOpportunities'),
      value: stats.activeOpportunities,
    },
    {
      label: t('organization.totalApplications'),
      value: stats.totalApplications,
    },
    {
      label: t('organization.newApplications'),
      value: stats.newApplications,
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-lg border border-neutral-200 bg-white p-4"
        >
          <p className="text-sm text-neutral-500">{card.label}</p>
          <p className="mt-2 text-2xl font-semibold text-neutral-950">
            {card.value}
          </p>
        </div>
      ))}
    </div>
  );
};

export default StatisticsOverview;
