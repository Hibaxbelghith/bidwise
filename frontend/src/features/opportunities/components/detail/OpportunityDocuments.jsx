import { ExternalLink, FileText } from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import { formatProjectDocumentType } from '../../utils/opportunityFormatters.js';

const OpportunityDocuments = ({ documents }) => {
  if (!documents || documents.length === 0) return null;

  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-neutral-900">Documents</h2>
        <Badge variant="outline">
          {documents.length} document{documents.length > 1 ? 's' : ''}
        </Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {documents.map((document, index) => (
          <div
            key={`${document.url}-${index}`}
            className="flex items-center justify-between gap-3 rounded-2xl border border-neutral-200 bg-neutral-50 p-4"
          >
            <div className="min-w-0">
              <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <FileText className="h-3.5 w-3.5" />
                {formatProjectDocumentType(document.type, document.label)}
              </p>
              <p className="mt-1 truncate text-sm font-medium text-neutral-900">
                {document.label || formatProjectDocumentType(document.type, document.label)}
              </p>
            </div>

            <Button asChild variant="outline" size="sm">
              <a href={document.url} target="_blank" rel="noopener noreferrer">
                Open
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
          </div>
        ))}
      </div>
    </section>
  );
};

export default OpportunityDocuments;
