import { BrainCircuit, FileSearch, ScanSearch, ShieldCheck } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../../components/ui/card.jsx';
import { formatNumber, percentFormatter } from './dashboard.Utils.js';

const moduleIconMap = {
  moderation: ShieldCheck,
  opportunity_enrichment: FileSearch,
  resume_semantic: BrainCircuit,
  recommendation_readiness: ScanSearch,
};

const formatPercentValue = (value) => `${percentFormatter.format(Number(value || 0))}%`;
const formatConfidenceValue = (value) => `${percentFormatter.format(Math.max(0, Math.min(Number(value || 0), 1)) * 100)}%`;

const formatDateTime = (value) => {
  if (!value) {
    return 'No recent activity';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'No recent activity';
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(parsed);
};

const normalizeCurrentIssue = (moduleKey, issue) => {
  const value = String(issue || '').trim();
  if (!value) {
    return 'No active issue';
  }

  if (moduleKey === 'resume_semantic') {
    if (value.toLowerCase().includes('marked failed during cleanup')) {
      return 'Some resume analyses failed during background processing.';
    }
  }

  return value;
};

const formatModuleSubhead = (moduleKey, moduleData) => {
  const provider = String(moduleData?.provider || '').trim();
  const model = String(moduleData?.model || '').trim();

  if (!provider && !model) {
    return 'Stored operational metrics only';
  }

  if (moduleKey === 'moderation') {
    if (provider === 'fallback' && model === 'provider-chain') {
      return 'Fallback result stored';
    }
    if (provider && model) {
      return `${provider} · ${model}`;
    }
    return provider || model;
  }

  return [provider, model].filter(Boolean).join(' · ');
};

const SummaryPair = ({ label, value }) => (
  <div className="space-y-1">
    <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">{label}</p>
    <p className="text-sm font-semibold text-neutral-900">{value}</p>
  </div>
);

const getModuleTone = (issue) => {
  if (issue) {
    return 'border-yellow-200 bg-yellow-50/60';
  }
  return 'border-neutral-200 bg-white';
};

const renderModuleDetails = (moduleKey, moduleData) => {
  switch (moduleKey) {
    case 'moderation':
      return (
        <>
          <SummaryPair
            label="Coverage"
            value={`${formatNumber(moduleData.processed)} / ${formatNumber(moduleData.total)} · ${formatPercentValue(moduleData.coverage)}`}
          />
          <SummaryPair
            label="Decisions"
            value={`${formatNumber(moduleData.approved)} approved · ${formatNumber(moduleData.pending_review)} pending · ${formatNumber(moduleData.rejected)} rejected`}
          />
          <SummaryPair
            label="Confidence"
            value={formatConfidenceValue(moduleData.average_confidence)}
          />
          <SummaryPair
            label="Human Overrides"
            value={`${formatNumber(moduleData.admin_overrides)} / ${formatNumber(moduleData.admin_reviewed)} · ${formatPercentValue(moduleData.override_rate)}`}
          />
        </>
      );
    case 'opportunity_enrichment':
      return (
        <>
          <SummaryPair
            label="Coverage"
            value={`${formatNumber(moduleData.processed)} / ${formatNumber(moduleData.total)} · ${formatPercentValue(moduleData.coverage)}`}
          />
          <SummaryPair
            label="Applied to Skills"
            value={formatNumber(moduleData.applied_to_skills)}
          />
          <SummaryPair
            label="Warnings"
            value={formatNumber(moduleData.with_warnings)}
          />
          <SummaryPair
            label="Confidence"
            value={formatConfidenceValue(moduleData.average_confidence)}
          />
        </>
      );
    case 'resume_semantic':
      return (
        <>
          <SummaryPair
            label="Coverage"
            value={`${formatNumber(moduleData.succeeded)} / ${formatNumber(moduleData.total)} · ${formatPercentValue(moduleData.coverage)}`}
          />
          <SummaryPair
            label="Status Mix"
            value={`${formatNumber(moduleData.failed)} failed · ${formatNumber(moduleData.pending)} pending · ${formatNumber(moduleData.empty)} empty`}
          />
          <SummaryPair
            label="Skipped"
            value={formatNumber(moduleData.skipped)}
          />
          <SummaryPair
            label="Confidence"
            value={formatConfidenceValue(moduleData.average_confidence)}
          />
        </>
      );
    case 'recommendation_readiness':
      return (
        <>
          <SummaryPair
            label="Profile Coverage"
            value={`${formatNumber(moduleData.profile_embeddings)} / ${formatNumber(moduleData.profile_total)} · ${formatPercentValue(moduleData.profile_coverage)}`}
          />
          <SummaryPair
            label="Opportunity Coverage"
            value={`${formatNumber(moduleData.opportunity_embeddings)} / ${formatNumber(moduleData.opportunity_total)} · ${formatPercentValue(moduleData.opportunity_coverage)}`}
          />
          <SummaryPair
            label="pgvector"
            value={formatNumber(moduleData.opportunity_pg_embeddings)}
          />
          <SummaryPair
            label="JobBERT"
            value={`${formatNumber(moduleData.profile_jobbert_embeddings)} profiles · ${formatNumber(moduleData.opportunity_jobbert_embeddings)} opportunities`}
          />
        </>
      );
    default:
      return null;
  }
};

const ModulePanel = ({ moduleKey, moduleData }) => {
  const Icon = moduleIconMap[moduleKey] || BrainCircuit;
  const issue = normalizeCurrentIssue(moduleKey, moduleData?.current_issue);
  const subhead = formatModuleSubhead(moduleKey, moduleData);

  return (
    <section className={`rounded-lg border p-5 ${getModuleTone(issue)}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-blue-600" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-neutral-950">{moduleData?.module || 'AI Module'}</h3>
          </div>
          <p className="mt-2 text-xs text-neutral-500">{subhead}</p>
        </div>
        <div className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700">
          {formatDateTime(moduleData?.last_updated_at)}
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {renderModuleDetails(moduleKey, moduleData)}
      </div>

      <div className="mt-5 border-t border-neutral-200 pt-4">
        <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">Current issue</p>
        <p className="mt-1 text-sm text-neutral-700">{issue}</p>
      </div>
    </section>
  );
};

const AISupervisionPanel = ({ aiSupervision }) => {
  const modules = aiSupervision?.modules || {};
  const entries = [
    ['moderation', modules.moderation],
    ['opportunity_enrichment', modules.opportunity_enrichment],
    ['resume_semantic', modules.resume_semantic],
    ['recommendation_readiness', modules.recommendation_readiness],
  ].filter(([, value]) => Boolean(value));

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Supervision</CardTitle>
        <CardDescription>
          Operational health for moderation, enrichment, resume analysis, and recommendation readiness.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 xl:grid-cols-2">
          {entries.map(([key, value]) => (
            <ModulePanel key={key} moduleKey={key} moduleData={value} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default AISupervisionPanel;
