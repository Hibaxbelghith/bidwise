import { Link } from 'react-router-dom';

import { Badge } from '../../components/ui/badge.jsx';
import { formatSimilarityScore } from './utils/similarity.js';

const OpportunityCard = ({ opportunity }) => {
  const title = opportunity?.titre || 'Untitled opportunity';
  const id = opportunity?.id;
  const similarity = formatSimilarityScore(opportunity?.similarity_score);

  if (!id) return null;

  return (
    <Link
      to={`/opportunities/${id}`}
      className="block rounded-md border border-neutral-200 px-4 py-3 transition-colors hover:border-blue-300"
    >
      <div className="flex items-start justify-between gap-3">
        <span className="font-medium text-neutral-900">{title}</span>
        <Badge variant="secondary">{similarity.percentage}%</Badge>
      </div>
      <p className="mt-2 text-xs text-neutral-600">
        {similarity.label}
      </p>
    </Link>
  );
};

export default OpportunityCard;
