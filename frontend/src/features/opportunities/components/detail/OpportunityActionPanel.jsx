import { Bookmark, Check, ExternalLink, Loader2, Lock, Send } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '../../../../components/ui/button.jsx';
import { Separator } from '../../../../components/ui/separator.jsx';
import OpportunitySnapshot from './OpportunitySnapshot.jsx';

const OpportunityActionPanel = ({
  snapshotProps,
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
  <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">

{/*     <h3 className="mb-4 text-base font-semibold text-neutral-900">Opportunity snapshot</h3>

    <OpportunitySnapshot {...snapshotProps} />

    <Separator className="my-5" />  */}

    {isUserAuthenticated ? (
      <div className="space-y-2">
        {isApplied ? (
          <div className="flex h-10 items-center justify-center gap-2 rounded-md border border-green-200 bg-green-50 text-sm font-semibold text-green-700">
            Applied
            <Check className="h-4 w-4" />
          </div>
        ) : canApply ? (
          <Button onClick={onApply} disabled={!canApply || isApplyingExternally} className="w-full">
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
        <Button variant="outline" onClick={onSave} className="w-full">
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
      </div>
    ) : (
      <div className="space-y-2">
        <Button asChild className="w-full">
          <Link to="/login">Login to unlock actions</Link>
        </Button>
        <Button variant="outline" disabled className="w-full">
          <Lock className="h-4 w-4" />
          Save and Apply locked
        </Button>
      </div>
    )}
  </div>
);

export default OpportunityActionPanel;
