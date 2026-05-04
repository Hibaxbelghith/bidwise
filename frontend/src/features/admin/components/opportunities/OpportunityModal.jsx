import { ExternalLink, X } from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import { formatDate, getSourceName, sourceClassName, statusClassName } from './opportunity.Utils.js';

const OpportunityModal = ({ opportunity, onClose }) => {
  if (!opportunity) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/60 px-4 py-6">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl" role="dialog" aria-modal="true">
        <div className="flex items-start justify-between gap-4 border-b border-neutral-200 p-5">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">{opportunity.title}</h2>
            <p className="mt-1 text-sm text-neutral-500">{opportunity.company_name || 'Unknown company'}</p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        <div className="space-y-4 p-5 text-sm">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className={sourceClassName(opportunity.source)}>
              {getSourceName(opportunity.source) || 'unknown'}
            </Badge>
            <Badge variant="outline" className={statusClassName(opportunity.status)}>
              {opportunity.status || 'unknown'}
            </Badge>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-xs font-medium uppercase text-neutral-500">Created</p>
              <p className="mt-1 text-neutral-900">{formatDate(opportunity.created_at)}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase text-neutral-500">ID</p>
              <p className="mt-1 text-neutral-900">{opportunity.id}</p>
            </div>
          </div>
          {opportunity.url ? (
            <a
              href={opportunity.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-sm font-medium text-blue-700 hover:text-blue-900"
            >
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              Open source URL
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default OpportunityModal;
