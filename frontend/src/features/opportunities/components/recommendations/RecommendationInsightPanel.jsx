import { Check, Sparkles, ThumbsUp } from 'lucide-react';

import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import { buildRecommendationViewModel } from '../../utils/recommendationUtils.js';
import RecommendationMatchBadge from './RecommendationMatchBadge.jsx';

export const RecommendationInsightSkeleton = ({ className = '' }) => (
  <section
    className={[
      'rounded-md border border-neutral-200 bg-white p-4 shadow-sm',
      className,
    ].join(' ')}
    aria-label="Loading AI recommendation insight"
  >
    <div className="animate-pulse space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="h-9 w-9 rounded-md bg-neutral-200" />
          <div className="space-y-2">
            <div className="h-4 w-36 rounded bg-neutral-200" />
            <div className="h-3 w-56 rounded bg-neutral-100" />
          </div>
        </div>
        <div className="h-7 w-28 rounded-full bg-neutral-100" />
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="h-8 rounded-md bg-neutral-100" />
        <div className="h-8 rounded-md bg-neutral-100" />
      </div>
    </div>
  </section>
);

const RecommendationInsightPanel = ({
  recommendation,
  compact = false,
  context = 'feed',
  className = '',
}) => {
  const { t } = useLanguage();
  const viewModel = buildRecommendationViewModel(recommendation, {
    context,
    reasonLimit: compact ? 3 : context === 'detail' ? 5 : 4,
    gapLimit: compact ? 3 : context === 'detail' ? 5 : 4,
    t,
  });

  if (!viewModel) return null;

  const chipTone = {
    strong: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    support: 'border-blue-200 bg-blue-50 text-blue-800',
    gap: 'border-amber-200 bg-amber-50 text-amber-800',
    neutral: 'border-neutral-200 bg-neutral-50 text-neutral-700',
  };

  return (
    <section
      className={[
        'rounded-md border p-4 shadow-sm',
        compact ? 'space-y-3' : 'space-y-4',
        viewModel.tone.panel,
        className,
      ].join(' ')}
      aria-label="AI recommendation insight"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="inline-flex min-w-0 items-start gap-3">
          <span
            className={[
              'inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md',
              viewModel.tone.icon,
            ].join(' ')}
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-neutral-950">{viewModel.panelTitle}</p>
            <p className="mt-0.5 text-sm text-neutral-600">{viewModel.matchSummary}</p>
          </div>
        </div>
        <RecommendationMatchBadge recommendation={recommendation} showConfidence />
      </div>

      {viewModel.signalChips.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {viewModel.signalChips.map((chip) => (
            <span
              key={chip.key}
              className={[
                'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold',
                chipTone[chip.tone] || chipTone.neutral,
              ].join(' ')}
            >
              {chip.label}
            </span>
          ))}
        </div>
      ) : null}

      {context === 'detail' ? (
        <div className="flex items-start gap-3 rounded-md border border-neutral-200 bg-neutral-50 p-3">
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-neutral-700">
            <ThumbsUp className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-neutral-950">{viewModel.verdictLabel}</p>
            <p className="mt-0.5 text-sm leading-5 text-neutral-600">{viewModel.verdictDescription}</p>
          </div>
        </div>
      ) : null}

      {viewModel.visibleReasons.length > 0 ? (
        <div className={['rounded-md p-3', viewModel.tone.surface].join(' ')}>
          <p className="text-xs font-semibold uppercase">{viewModel.reasonsTitle || t('opportunities.detail.whyThisMatches')}</p>
          <ul className="mt-2 grid gap-2 text-sm leading-5 sm:grid-cols-2">
            {viewModel.visibleReasons.map((reason) => (
              <li key={reason} className="flex items-start gap-2">
                <Check className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {viewModel.hasGaps ? (
        <div className="flex flex-col gap-2 border-t border-neutral-100 pt-3 sm:flex-row sm:items-center">
          <p className="text-xs font-semibold uppercase text-neutral-600">{viewModel.reviewLabel}</p>
          <div className="flex flex-wrap gap-2">
            {viewModel.gaps.map((gap) => (
              <span
                key={gap}
                className="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs font-semibold text-neutral-700"
              >
                {gap}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
};

export default RecommendationInsightPanel;
