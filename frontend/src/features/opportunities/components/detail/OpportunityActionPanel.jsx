import { Bookmark, Check, ExternalLink, Lock } from 'lucide-react';
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
}) => (
  <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <h3 className="mb-4 text-base font-semibold text-neutral-900">Opportunity snapshot</h3>

    <OpportunitySnapshot {...snapshotProps} />

    <Separator className="my-5" />

    {isUserAuthenticated ? (
      <div className="space-y-2">
        <Button onClick={onApply} disabled={!canApply} className="w-full">
          {primaryActionLabel}
          <ExternalLink className="h-4 w-4" />
        </Button>
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
