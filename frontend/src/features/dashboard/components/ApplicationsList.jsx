import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Briefcase, Building2, MapPin, Calendar } from 'lucide-react';
import { Badge } from '../../../components/ui/badge.jsx';
import { Button } from '../../../components/ui/button';
import { Card, CardContent } from '../../../components/ui/card';
import {
  getApplicationDatePrefix,
  getApplicationStatusMeta,
} from '../../applications/applicationStatusUi.js';

const WITHDRAWABLE = new Set(['SUBMITTED', 'VIEWED_BY_ORGANIZATION']);
const CONTINUABLE_EXTERNAL_STATUSES = new Set(['EXTERNAL_REMIND_LATER']);

const formatDate = (value) => {
  if (!value) return '';
  try {
    return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' })
      .format(new Date(value));
  } catch {
    return value;
  }
};

const ApplicationStatusBadge = ({ statut }) => {
  const config = getApplicationStatusMeta(statut, 'candidate');
  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  );
};

const WithdrawConfirmDialog = ({ title, onConfirm, onCancel, isSubmitting }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4">
    <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl" role="dialog" aria-modal="true">
      <h2 className="text-base font-semibold text-neutral-950">
        Cancel your application?
      </h2>
      <p className="mt-2 text-sm leading-6 text-neutral-600">
        You will no longer be considered for &quot;{title}&quot;. This action cannot be undone.
      </p>
      <div className="mt-5 flex justify-end gap-3">
        <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={isSubmitting}>
          Keep application
        </Button>
        <Button
          type="button"
          size="sm"
          className="bg-red-600 text-white hover:bg-red-700"
          onClick={onConfirm}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Cancelling...' : 'Yes, cancel it'}
        </Button>
      </div>
    </div>
  </div>
);

const ApplicationCard = ({ application, onWithdraw }) => {
  const [confirming, setConfirming] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);
  const [withdrawError, setWithdrawError] = useState('');

  const datePrefix = getApplicationDatePrefix(application.statut, 'candidate');

  const handleConfirm = async () => {
    try {
      setWithdrawing(true);
      setWithdrawError('');
      await onWithdraw(application.id);
      setConfirming(false);
    } catch {
      setWithdrawError('Unable to cancel your application. Please try again.');
    } finally {
      setWithdrawing(false);
    }
  };

  return (
    <>
      {confirming && (
        <WithdrawConfirmDialog
          title={application.opportunity_title}
          onConfirm={handleConfirm}
          onCancel={() => setConfirming(false)}
          isSubmitting={withdrawing}
        />
      )}
      <Card className="hover:border-blue-300 transition-colors">
        <CardContent className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-3 mb-2">
                <Link
                  to={`/opportunities/${application.opportunity_id}`}
                  className="text-lg font-semibold text-neutral-900 hover:text-blue-600 truncate"
                >
                  {application.opportunity_title}
                </Link>
                <ApplicationStatusBadge statut={application.statut} />
              </div>
              <div className="flex flex-wrap items-center gap-4 text-sm text-neutral-600">
                {application.organisation_name && (
                  <span className="flex items-center gap-1">
                    <Building2 className="w-4 h-4 shrink-0" aria-hidden="true" />
                    {application.organisation_name}
                  </span>
                )}
                {application.ville && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-4 h-4 shrink-0" aria-hidden="true" />
                    {application.ville}
                  </span>
                )}
                {application.submitted_at && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4 shrink-0" aria-hidden="true" />
                    {datePrefix} {formatDate(application.submitted_at)}
                  </span>
                )}
              </div>
              {withdrawError && (
                <p className="mt-2 text-sm text-red-600">{withdrawError}</p>
              )}
            </div>
            <div className="flex shrink-0 gap-2">
              <Button asChild size="sm">
                <Link to={`/opportunities/${application.opportunity_id}`}>View</Link>
              </Button>
              {CONTINUABLE_EXTERNAL_STATUSES.has(application.statut) && (
                <Button asChild variant="outline" size="sm">
                  <Link to={`/opportunities/${application.opportunity_id}?continueApplication=1`}>
                    Continue application
                  </Link>
                </Button>
              )}
              {WITHDRAWABLE.has(application.statut) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirming(true)}
                >
                  Cancel application
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
};

const ApplicationsList = ({ applications, isLoading, error, onWithdraw }) => {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-neutral-500">
          Loading your applications...
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-red-600">
          {error}
        </CardContent>
      </Card>
    );
  }

  if (applications.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Briefcase className="w-12 h-12 text-neutral-300 mx-auto mb-4" aria-hidden="true" />
          <p className="text-neutral-600 mb-4">No applications yet</p>
          <Button asChild>
            <Link to="/opportunities">Start Applying</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {applications.map((app) => (
        <ApplicationCard key={app.id} application={app} onWithdraw={onWithdraw} />
      ))}
    </div>
  );
};

export default ApplicationsList;
