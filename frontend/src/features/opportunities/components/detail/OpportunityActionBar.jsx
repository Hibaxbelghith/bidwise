import { Bookmark, Check, ExternalLink, Loader2, Lock, Send } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '../../../../components/ui/button.jsx';

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
}) => (
  <div className="fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-white/95 backdrop-blur lg:hidden">
    <div className="mx-auto flex max-w-6xl gap-3 px-4 py-3 sm:px-6 lg:px-8">
      {isUserAuthenticated ? (
        <>
          <Button variant="outline" onClick={onSave} className="flex-1">
            {isSaved ? (
              <>
                Saved
                <Check className="h-4 w-4" />
              </>
            ) : (
              <>
                Save
                <Bookmark className="h-4 w-4" />
              </>
            )}
          </Button>
          {isApplied ? (
            <div className="flex h-10 flex-1 items-center justify-center gap-2 rounded-md border border-green-200 bg-green-50 text-sm font-semibold text-green-700">
              Applied
              <Check className="h-4 w-4" />
            </div>
          ) : canApply ? (
            <Button onClick={onApply} disabled={!canApply || isApplyingExternally} className="flex-1">
              {isApplyingExternally ? 'Opening application...' : primaryActionLabel}
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
            <Link to="/login">Login to unlock</Link>
          </Button>
          <Button variant="outline" disabled className="flex-1">
            <Lock className="h-4 w-4" />
            Actions locked
          </Button>
        </>
      )}
    </div>
  </div>
);

export default OpportunityActionBar;
