import { FileText, TrendingUp, Users, CheckCircle } from 'lucide-react';

const StatisticsOverview = ({ stats }) => {
  const cards = [
    {
      label: 'Published Opportunities',
      value: stats.totalOpportunities,
    },
    {
      label: 'Active Opportunities',
      value: stats.activeOpportunities,
    },
    {
      label: 'Total Applications',
      value: stats.totalApplications,
    },
    {
      label: 'New Applications',
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
