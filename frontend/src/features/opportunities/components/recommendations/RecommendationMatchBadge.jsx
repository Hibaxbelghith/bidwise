import { Sparkles } from 'lucide-react';

import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import { buildRecommendationViewModel } from '../../utils/recommendationUtils.js';

const MatchRing = ({ percent, color }) => {
  if (!percent || percent <= 0) {
    return (
      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/80">
        <Sparkles className="h-3 w-3" aria-hidden="true" />
      </span>
    );
  }

  return (
    <span
      className="inline-flex h-5 w-5 items-center justify-center rounded-full"
      style={{
        background: `conic-gradient(${color} ${percent * 3.6}deg, rgba(255,255,255,.8) 0deg)`,
      }}
      aria-hidden="true"
    >
      <span className="h-3 w-3 rounded-full bg-white" />
    </span>
  );
};

const RecommendationMatchBadge = ({ recommendation, className = '', showConfidence = false }) => {
  const { t } = useLanguage();
  const viewModel = buildRecommendationViewModel(recommendation, { t });
  if (!viewModel) return null;

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold shadow-sm shadow-neutral-950/[0.03]',
        viewModel.tone.badge,
        className,
      ].join(' ')}
    >
      <MatchRing percent={viewModel.scorePercent} color={viewModel.tone.ring} />
      <span>{viewModel.scoreText}</span>
      {showConfidence ? (
        <>
          <span className="hidden h-1 w-1 rounded-full bg-current opacity-50 sm:inline-block" aria-hidden="true" />
          <span className="hidden sm:inline">{viewModel.confidenceLabel}</span>
        </>
      ) : null}
    </span>
  );
};

export default RecommendationMatchBadge;
