import { Link } from 'react-router-dom';
import { ArrowRight, FileText, Sparkles } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const ResumeFitCtaCard = ({
  title = null,
  body = null,
  ctaLabel = null,
  compact = false,
  className = '',
}) => {
  const { t } = useLanguage();
  const resolvedTitle = title || t('opportunities.detail.resumeMatchTitle');
  const resolvedBody = body || t('opportunities.detail.resumeMatchBody');
  const resolvedCtaLabel = ctaLabel || t('profile.uploadResume');

  return (
  <section
    className={[
      'rounded-md border border-blue-200 bg-white p-5 shadow-sm',
      compact ? 'space-y-3' : 'space-y-4',
      className,
    ].join(' ')}
  >
    <div className="flex items-start gap-3">
      <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-700">
        <FileText className="h-5 w-5" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase text-blue-700">
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          {t('opportunities.detail.resumeMatchEyebrow')}
        </p>
        <h2 className="mt-1 text-base font-semibold text-neutral-950">{resolvedTitle}</h2>
        <p className="mt-1 text-sm leading-6 text-neutral-600">{resolvedBody}</p>
      </div>
    </div>

    <Button asChild className="w-full bg-blue-600 text-white hover:bg-blue-700 sm:w-auto">
      <Link to="/profile">
        {resolvedCtaLabel}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
    </Button>
  </section>
  );
};

export default ResumeFitCtaCard;
