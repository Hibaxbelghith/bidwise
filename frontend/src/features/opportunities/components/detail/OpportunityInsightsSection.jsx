import { Link } from 'react-router-dom';

import { Button } from '../../../../components/ui/button.jsx';
import LockPreviewCard from './LockPreviewCard.jsx';

const OpportunityInsightsSection = ({
  isUserAuthenticated,
  semanticMatchScore,
  matchBullets,
  aiDraft,
}) => {
  if (!isUserAuthenticated) {
    return (
      <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-neutral-900">Unlock AI Intelligence</h2>
        <p className="mb-4 text-sm leading-6 text-neutral-600">
          Core opportunity data stays open. Login to unlock match score, recommendation
          intelligence, and AI application support.
        </p>

        <div className="grid gap-3 md:grid-cols-3">
          <LockPreviewCard
            title="Match score"
            body="See a numeric fit score to quickly prioritize the best opportunities."
          />
          <LockPreviewCard
            title="Why this matches"
            body="Understand fit drivers such as skills overlap, experience, and location."
          />
          <LockPreviewCard
            title="AI draft assistant"
            body="Generate a tailored application draft and iterate faster."
          />
        </div>

        <Button asChild className="mt-4 w-full sm:w-auto">
          <Link to="/login">Login to unlock AI features</Link>
        </Button>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-neutral-900">AI Insights</h2>

      <div className="space-y-3">
        <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Match score</p>
          <div className="mt-2 flex items-center gap-3">
            <p className="text-3xl font-bold text-neutral-900">
              {semanticMatchScore !== null ? `${semanticMatchScore}%` : 'N/A'}
            </p>
            <div className="h-2 w-24 overflow-hidden rounded-full bg-neutral-200">
              <div
                className="h-full rounded-full bg-blue-600"
                style={{ width: `${semanticMatchScore ?? 0}%` }}
              />
            </div>
          </div>
          <p className="mt-2 text-xs text-neutral-600">
            Based on semantic similarity between this opportunity and related listings.
          </p>
        </div>

        <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Why this matches you
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-neutral-800">
            {matchBullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            AI-generated application draft
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-neutral-800">{aiDraft}</p>
          <p className="mt-2 text-xs text-neutral-600">
            CV and cover letter automation will expand in Sprint 3.
          </p>
        </div>
      </div>
    </section>
  );
};

export default OpportunityInsightsSection;
