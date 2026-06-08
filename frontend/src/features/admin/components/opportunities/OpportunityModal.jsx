import { AlertTriangle, Ban, Check, CheckCircle2, ExternalLink, Info, ShieldAlert, X } from 'lucide-react';

import { Badge } from '../../../../components/ui/badge.jsx';
import { Button } from '../../../../components/ui/button.jsx';
import {
  formatDate,
  formatDateTime,
  getSourceName,
  originClassName,
  originLabel,
  sourceClassName,
  statusClassName,
  statusLabel,
  typeLabel,
} from './opportunity.Utils.js';

const formatValue = (value) => {
  if (value === null || value === undefined || value === '') return '-';
  if (Array.isArray(value)) return value.length ? value.join(', ') : '-';
  return String(value);
};

const formatExperience = (min, max) => {
  if (min === null && max === null) return '-';
  if (min !== null && max !== null) return `${min} - ${max} years`;
  if (min !== null) return `${min}+ years`;
  return `Up to ${max} years`;
};

const moderationCategoryLabel = (category) => {
  const value = String(category || '').toLowerCase();
  if (value === 'legitimate_opportunity') return 'Legitimate opportunity';
  if (value === 'scam') return 'Scam risk';
  if (value === 'mlm_or_pyramid') return 'MLM / pyramid risk';
  if (value === 'advertisement') return 'Advertisement';
  if (value === 'inappropriate_content') return 'Inappropriate content';
  if (value === 'irrelevant') return 'Irrelevant content';
  if (value === 'unclear') return 'Unclear';
  return category || 'Unknown';
};

const decisionLabel = (decision) => {
  const value = String(decision || '').toLowerCase();
  if (value === 'approved') return 'Approved for publication';
  if (value === 'pending_review') return 'Needs admin review';
  if (value === 'needs_changes') return 'Needs organization changes';
  if (value === 'rejected') return 'High-risk content';
  return decision || 'Unknown';
};

const moderationStyle = (decision) => {
  const value = String(decision || '').toLowerCase();
  if (value === 'approved') {
    return {
      icon: CheckCircle2,
      className: 'border-green-200 bg-green-50 text-green-800',
      badge: 'border-green-200 bg-white text-green-700',
    };
  }
  if (value === 'rejected' || value === 'needs_changes') {
    return {
      icon: ShieldAlert,
      className: 'border-red-200 bg-red-50 text-red-800',
      badge: 'border-red-200 bg-white text-red-700',
    };
  }
  return {
    icon: AlertTriangle,
    className: 'border-blue-200 bg-blue-50 text-blue-800',
    badge: 'border-blue-200 bg-white text-blue-700',
  };
};

const confidenceHelpText = (confidence) => {
  const score = Number(confidence || 0);
  if (score >= 0.88) return 'The AI is highly confident in this classification.';
  if (score >= 0.7) return 'The AI found a meaningful signal, but admin review is still useful.';
  return 'The AI is not confident enough; manual review is recommended.';
};

const aiEngineLabel = (summary) => {
  if (!summary?.provider && !summary?.model) return '-';
  if (String(summary.provider || '').toLowerCase() === 'fallback') return 'BidWise AI moderation engine';
  if (String(summary.provider || '').toLowerCase() === 'gemini') return 'Gemini moderation engine';
  return 'AI moderation engine';
};

const DetailItem = ({ label, value, wide = false }) => (
  <div className={wide ? 'sm:col-span-2' : ''}>
    <p className="text-xs font-medium uppercase text-neutral-500">{label}</p>
    <p className="mt-1 break-words text-sm text-neutral-900">{formatValue(value)}</p>
  </div>
);

const Skills = ({ skills }) => {
  if (!skills?.length) return <DetailItem label="Skills" value="-" wide />;

  return (
    <div className="sm:col-span-2">
      <p className="text-xs font-medium uppercase text-neutral-500">Skills</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {skills.map((skill) => (
          <Badge key={skill} variant="outline" className="border-neutral-200 bg-neutral-50 text-neutral-700">
            {skill}
          </Badge>
        ))}
      </div>
    </div>
  );
};

const TypeSpecificDetails = ({ details }) => {
  if (!details || Object.keys(details).length === 0) return null;

  const flatDetails = Object.entries(details).flatMap(([section, values]) => (
    Object.entries(values || {}).map(([key, value]) => ({
      key: `${section}.${key}`,
      label: key.replaceAll('_', ' '),
      value: Array.isArray(value)
        ? `${value.length} item${value.length > 1 ? 's' : ''}`
        : value,
    }))
  ));

  if (!flatDetails.length) return null;

  return (
    <section className="rounded-lg border border-neutral-200 p-4">
      <h3 className="text-sm font-semibold text-neutral-900">Type-specific details</h3>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {flatDetails.slice(0, 12).map((item) => (
          <DetailItem key={item.key} label={item.label} value={item.value} />
        ))}
      </div>
    </section>
  );
};

const ModerationDetails = ({ summary }) => {
  if (!summary) return null;

  const style = moderationStyle(summary.final_decision || summary.decision);
  const Icon = style.icon;

  return (
    <section className={`rounded-lg border p-4 ${style.className}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold">AI moderation result</h3>
            <p className="mt-1 break-words text-sm">
              {decisionLabel(summary.final_decision || summary.decision)}
            </p>
          </div>
        </div>
        <Badge variant="outline" className={style.badge}>
          {moderationCategoryLabel(summary.category)}
        </Badge>
      </div>

      <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase text-neutral-500">AI confidence</p>
          <p className="mt-1 text-sm font-semibold text-neutral-900">
            {summary.confidence !== undefined ? `${Math.round(Number(summary.confidence || 0) * 100)}%` : '-'}
          </p>
          <p className="mt-1 text-xs leading-5 text-neutral-600">{confidenceHelpText(summary.confidence)}</p>
        </div>
        <DetailItem label="AI engine" value={aiEngineLabel(summary)} />
        <DetailItem label="AI explanation" value={summary.reason} wide />
      </div>

      {String(summary.final_decision || '').toLowerCase() !== 'approved' ? (
        <div className="mt-4 flex gap-2 rounded-md border border-current/20 bg-white/60 p-3 text-xs leading-5">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>
            This opportunity is not public yet. Review the content, then approve it or keep it blocked from publication.
          </p>
        </div>
      ) : null}
    </section>
  );
};

const canModerate = (opportunity) => (
  opportunity?.published_by === 'organization'
  && String(opportunity?.status || '').toUpperCase() === 'PENDING_REVIEW'
);

const OpportunityModal = ({ opportunity, isModerating = false, onClose, onApprove, onReject }) => {
  if (!opportunity) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/60 px-3 py-4 sm:px-6">
      <div className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-lg bg-white shadow-xl" role="dialog" aria-modal="true">
        <div className="flex items-start justify-between gap-4 border-b border-neutral-200 p-5">
          <div className="min-w-0">
            <h2 className="break-words text-lg font-semibold leading-7 text-neutral-900">
              {opportunity.title}
            </h2>
            <p className="mt-1 break-words text-sm text-neutral-500">
              {opportunity.company_name || 'Unknown company'}
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        <div className="space-y-5 overflow-y-auto p-5 text-sm">
          {canModerate(opportunity) ? (
            <div className="flex flex-col gap-3 rounded-lg border border-blue-100 bg-blue-50/70 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-blue-950">Admin decision required</p>
                <p className="mt-1 text-xs leading-5 text-blue-800">
                  Approving publishes this opportunity. Rejecting archives it and keeps a full audit trail.
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  disabled={isModerating}
                  onClick={() => onReject?.(opportunity)}
                  className="border-red-200 bg-white text-red-700 hover:bg-red-50"
                >
                  <Ban className="h-4 w-4" aria-hidden="true" />
                  Reject
                </Button>
                <Button
                  type="button"
                  disabled={isModerating}
                  onClick={() => onApprove?.(opportunity)}
                >
                  <Check className="h-4 w-4" aria-hidden="true" />
                  {isModerating ? 'Saving' : 'Approve'}
                </Button>
              </div>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{typeLabel(opportunity.type)}</Badge>
            <Badge variant="outline" className={originClassName(opportunity)}>
              {originLabel(opportunity)}
            </Badge>
            <Badge variant="outline" className={sourceClassName(opportunity.source)}>
              {getSourceName(opportunity.source) || 'unknown source'}
            </Badge>
            <Badge variant="outline" className={statusClassName(opportunity.status)}>
              {statusLabel(opportunity.status)}
            </Badge>
          </div>

          <ModerationDetails summary={opportunity.moderation_summary} />

          <section className="rounded-lg border border-neutral-200 p-4">
            <h3 className="text-sm font-semibold text-neutral-900">Opportunity overview</h3>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <DetailItem label="Company" value={opportunity.company_name || 'Unknown company'} />
              <DetailItem label="Organization email" value={opportunity.organization_email} />
              <DetailItem label="Location" value={opportunity.location} />
              <DetailItem label="Published" value={formatDateTime(opportunity.published_at)} />
              <DetailItem label="Added to BidWise" value={formatDateTime(opportunity.created_at)} />
              <DetailItem label="Contract" value={opportunity.contract} />
              <DetailItem
                label="Availability"
                value={{
                  REMOTE: 'Remote',
                  HYBRID: 'Hybrid',
                  ON_SITE: 'On site',
                }[String(opportunity.availability || '').trim().toUpperCase()] || opportunity.availability}
              />
              <DetailItem label="Experience" value={formatExperience(opportunity.experience_min, opportunity.experience_max)} />
              <DetailItem label="Salary" value={opportunity.salary} />
              <DetailItem label="ID" value={opportunity.id} />
              <DetailItem label="Source" value={getSourceName(opportunity.source) || 'unknown source'} />
              <Skills skills={opportunity.skills} />
            </div>
          </section>

          {opportunity.description ? (
            <section className="rounded-lg border border-neutral-200 p-4">
              <h3 className="text-sm font-semibold text-neutral-900">Description</h3>
              <p className="mt-3 whitespace-pre-line break-words leading-6 text-neutral-700">
                {opportunity.description}
              </p>
            </section>
          ) : null}

          <TypeSpecificDetails details={opportunity.opportunity_details} />

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
