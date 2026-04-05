import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Building2, Calendar, ExternalLink } from 'lucide-react';

import { Badge } from '../../components/ui/badge.jsx';
import { Button } from '../../components/ui/button.jsx';
import { Separator } from '../../components/ui/separator.jsx';
import { useOpportunityDetail, useSimilarOpportunities } from './useOpportunities';
import SimilarOpportunities from './SimilarOpportunities.jsx';
import { cleanDescription } from './utils/text.js';

const TYPE_LABELS = {
  EMPLOI: 'Job',
  STAGE: 'Internship',
  RECHERCHE: 'Research',
  PROJET: 'Project',
  FINANCEMENT: 'Funding',
};

const STATUS_LABELS = {
  ACTIVE: 'Active',
  EXPIREE: 'Expired',
  ARCHIVEE: 'Archived',
};

const formatDate = (value) => {
  if (!value) return 'N/A';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
};

const OpportunityDetail = () => {
  const { id } = useParams();
  const { opportunity, loading, error } = useOpportunityDetail(id);

  const {
    similarOpportunities,
    loading: similarLoading,
  } = useSimilarOpportunities(opportunity?.id, 5, Boolean(opportunity?.id));

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-6 text-neutral-700">
          Loading opportunity details...
        </div>
      </div>
    );
  }

  if (error || !opportunity) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
        <Link to="/opportunities" className="inline-flex items-center gap-2 text-neutral-600">
          <ArrowLeft className="h-4 w-4" />
          Back to opportunities
        </Link>
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
          {error || 'Opportunity not found'}
        </div>
      </div>
    );
  }

  const visitSourceUrl = opportunity.url || opportunity.source?.url || '';

  return (
    <div className="min-h-screen bg-white">
      <div className="border-b border-neutral-200 bg-neutral-50">
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
          <Link
            to="/opportunities"
            className="mb-6 inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to opportunities
          </Link>

          <div className="flex items-start gap-6">
            <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-lg border border-neutral-200 bg-white">
              <Building2 className="h-8 w-8 text-neutral-400" />
            </div>
            <div className="flex-1">
              <div className="mb-2 flex flex-wrap items-center gap-3">
                <h1 className="text-3xl font-bold text-neutral-900">
                  {opportunity.titre || 'Untitled opportunity'}
                </h1>
                <Badge>{TYPE_LABELS[opportunity.type_opportunite] || opportunity.type_opportunite}</Badge>
                <Badge variant={opportunity.statut === 'ACTIVE' ? 'default' : 'outline'}>
                  {STATUS_LABELS[opportunity.statut] || opportunity.statut}
                </Badge>
              </div>
              <p className="text-lg text-neutral-600">
                {opportunity.organisation_nom || opportunity.source?.nom || 'Unknown organization'}
              </p>
              <div className="mt-3 flex flex-wrap gap-4 text-sm text-neutral-600">
                <span className="inline-flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Published: {formatDate(opportunity.date_publication)}
                </span>
                <span className="inline-flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Deadline: {formatDate(opportunity.date_limite)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="space-y-8 lg:col-span-2">
            <section>
              <h2 className="mb-4 text-2xl font-semibold text-neutral-900">Description</h2>
              <p className="whitespace-pre-wrap leading-relaxed text-neutral-700">
                {cleanDescription(opportunity.description)}
              </p>
            </section>

            <Separator />

            <section>
              <h2 className="mb-4 text-2xl font-semibold text-neutral-900">
                Similar Opportunities
              </h2>
              <SimilarOpportunities opportunities={similarOpportunities} loading={similarLoading} />
            </section>
          </div>

          <div className="lg:col-span-1">
            <div className="sticky top-24 rounded-lg border border-neutral-200 bg-neutral-50 p-6">
              <h3 className="mb-4 font-semibold text-neutral-900">Opportunity Details</h3>
              <dl className="space-y-4">
                <div>
                  <dt className="mb-1 text-sm text-neutral-500">Source</dt>
                  <dd className="text-neutral-900">{opportunity.source?.nom || 'Unknown source'}</dd>
                </div>
                <div>
                  <dt className="mb-1 text-sm text-neutral-500">Type</dt>
                  <dd className="text-neutral-900">
                    {TYPE_LABELS[opportunity.type_opportunite] || opportunity.type_opportunite || 'N/A'}
                  </dd>
                </div>
                <div>
                  <dt className="mb-1 text-sm text-neutral-500">Published</dt>
                  <dd className="text-neutral-900">{formatDate(opportunity.date_publication)}</dd>
                </div>
              </dl>

              {visitSourceUrl && (
                <>
                  <Separator className="my-6" />
                  <Button asChild className="w-full">
                    <a href={visitSourceUrl} target="_blank" rel="noopener noreferrer">
                      Visit Source
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </a>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OpportunityDetail;
