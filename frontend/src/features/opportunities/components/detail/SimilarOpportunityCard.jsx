import { Link } from 'react-router-dom';

import { Badge } from '../../../../components/ui/badge.jsx';
import { buildSimilarOpportunityCardViewModel } from '../../viewModels/opportunityList.vm.js';

const SimilarOpportunityCard = ({ opportunity }) => {
  const viewModel = buildSimilarOpportunityCardViewModel(opportunity);
  const { id, title, companyName, similarity } = viewModel;

  if (!id) return null;

  return (
    <Link
      to={`/opportunities/${id}`}
      className="block rounded-2xl border border-neutral-200 bg-white px-4 py-3 transition-colors hover:border-blue-300"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-neutral-900">{title}</p>
          <p className="mt-1 text-xs text-neutral-600">{companyName}</p>
        </div>
        <Badge variant="secondary">{similarity.percentage}%</Badge>
      </div>
      <p className="mt-2 text-xs text-neutral-600">{similarity.label}</p>
    </Link>
  );
};

export default SimilarOpportunityCard;
