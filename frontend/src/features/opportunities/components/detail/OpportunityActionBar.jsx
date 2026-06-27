import { Bookmark, Check, ExternalLink, Loader2, Lock, Send } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';

const OpportunityActionBar = ({
  isUserAuthenticated,
  isSaved,
  canApply,
  primaryActionLabel,
  onApply,
  onSave,
  isApplied,
  isDirectApplication,
  isApplyingExternally,
}) => {
  const { t } = useLanguage();
  const translatedPrimaryActionLabel =
    primaryActionLabel === 'Apply'
      ? t('opportunities.detail.apply')
      : primaryActionLabel === 'See on MarchesPublics.gov.tn'
        ? t('opportunities.detail.seeOnSource')
        : primaryActionLabel;

  return (
  <div className="fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-white/95 backdrop-blur lg:hidden">
    <div className="mx-auto flex max-w-6xl gap-3 px-4 py-3 sm:px-6 lg:px-8">
      {isUserAuthenticated ? (
        <>
          <Button variant="outline" onClick={onSave} className="flex-1">
            {isSaved ? (
              <>
                {t('opportunities.card.saved')}
                <Check className="h-4 w-4" />
              </>
            ) : (
              <>
                {t('opportunities.card.save')}
                <Bookmark className="h-4 w-4" />
              </>
            )}
          </Button>
          {isApplied ? (
            <div className="flex h-10 flex-1 items-center justify-center gap-2 rounded-md border border-green-200 bg-green-50 text-sm font-semibold text-green-700">
              {t('opportunities.detail.applied')}
              <Check className="h-4 w-4" />
            </div>
          ) : canApply ? (
            <Button onClick={onApply} disabled={!canApply || isApplyingExternally} className="flex-1">
              {isApplyingExternally ? t('opportunities.detail.openingApplication') : translatedPrimaryActionLabel}
              {isApplyingExternally ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isDirectApplication ? (
                <Send className="h-4 w-4" />
              ) : (
                <ExternalLink className="h-4 w-4" />
              )}
            </Button>
          ) : null}
        </>
      ) : (
        <>
          <Button asChild className="flex-1">
            <Link to="/login">{t('opportunities.detail.loginUnlock')}</Link>
          </Button>
          <Button variant="outline" disabled className="flex-1">
            <Lock className="h-4 w-4" />
            {t('opportunities.detail.actionsLocked')}
          </Button>
        </>
      )}
    </div>
  </div>
  );
};

export default OpportunityActionBar;
