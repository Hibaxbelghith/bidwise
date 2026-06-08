import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import {
  ORGANIZATION_OPPORTUNITY_STATUS_DOT_CLASSES,
  ORGANIZATION_OPPORTUNITY_STATUS_LABELS,
} from '../utils/organizationOpportunityFormatters.js';

const STATUS_TARGET_ACTIONS = {
  ACTIVE: { SUSPENDUE: 'suspend', FERMEE: 'close' },
  SUSPENDUE: { ACTIVE: 'activate', FERMEE: 'close' },
  PENDING_REVIEW: { ACTIVE: 'activate', SUSPENDUE: 'suspend', FERMEE: 'close' },
  FERMEE: { ACTIVE: 'activate', SUSPENDUE: 'suspend' },
  REJECTED: { FERMEE: 'close' },
};

const STATUS_MENU_OPTIONS = {
  ACTIVE: ['ACTIVE', 'SUSPENDUE', 'FERMEE'],
  SUSPENDUE: ['ACTIVE', 'SUSPENDUE', 'FERMEE'],
  PENDING_REVIEW: ['ACTIVE', 'SUSPENDUE', 'FERMEE'],
  REJECTED: ['REJECTED', 'FERMEE'],
  FERMEE: ['ACTIVE', 'SUSPENDUE', 'FERMEE'],
  ARCHIVEE: ['ARCHIVEE'],
  EXPIREE: ['EXPIREE'],
};

export const ORGANIZATION_OPPORTUNITY_EDITABLE_STATUSES = new Set([
  'ACTIVE',
  'PENDING_REVIEW',
  'REJECTED',
  'SUSPENDUE',
]);

export const statusFallbackForAction = (opportunity, action) => {
  if (action === 'suspend') return 'SUSPENDUE';
  if (action === 'close') return 'FERMEE';
  if (action === 'activate' && opportunity.status === 'PENDING_REVIEW') return 'PENDING_REVIEW';
  if (action === 'activate' && opportunity.suspended_from === 'PENDING_REVIEW') return 'PENDING_REVIEW';
  if (
    action === 'activate'
    && opportunity.status === 'FERMEE'
    && ['PENDING_REVIEW', 'REJECTED'].includes(opportunity.closed_from)
  ) {
    return 'PENDING_REVIEW';
  }
  return 'ACTIVE';
};

export const OrganizationOpportunityStatusLabel = ({ status }) => (
  <span className="flex min-w-0 items-center gap-2">
    <span
      className={`h-2 w-2 shrink-0 rounded-full ${
        ORGANIZATION_OPPORTUNITY_STATUS_DOT_CLASSES[status] || 'bg-red-700'
      }`}
      aria-hidden="true"
    />
    <span className="truncate">
      {ORGANIZATION_OPPORTUNITY_STATUS_LABELS[status] || status}
    </span>
  </span>
);

export const OrganizationOpportunityStatusSelect = ({ opportunity, disabled, onAction }) => {
  const transitions = STATUS_TARGET_ACTIONS[opportunity.status] || {};
  const options = STATUS_MENU_OPTIONS[opportunity.status] || [opportunity.status];
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!containerRef.current?.contains(event.target)) setIsOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setIsOpen(false);
    };

    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [isOpen]);

  const handleValueChange = (targetStatus) => {
    setIsOpen(false);
    if (targetStatus === opportunity.status) return;
    const action = transitions[targetStatus];
    if (action) onAction(opportunity, action);
  };

  return (
    <div ref={containerRef} className="relative w-44">
      <button
        type="button"
        className="flex h-11 w-full items-center justify-between gap-3 rounded-lg border border-neutral-300 bg-white px-3 text-left text-sm font-medium text-neutral-900 shadow-sm transition hover:border-neutral-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={`Change status for ${opportunity.title}`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        disabled={disabled || options.length === 1}
        onClick={() => setIsOpen((current) => !current)}
      >
        <OrganizationOpportunityStatusLabel status={opportunity.status} />
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-neutral-600 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {isOpen ? (
        <div
          className="absolute left-0 top-full z-30 mt-1.5 w-full overflow-hidden rounded-lg border border-neutral-200 bg-white p-1.5 shadow-xl"
          role="listbox"
          aria-label="Opportunity status"
        >
          {options.map((status) => {
            const isCurrent = status === opportunity.status;
            return (
              <button
                key={status}
                type="button"
                role="option"
                aria-selected={isCurrent}
                className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2.5 text-left text-sm transition ${
                  isCurrent
                    ? 'bg-neutral-100 font-medium text-neutral-950'
                    : 'text-neutral-700 hover:bg-neutral-50'
                }`}
                onClick={() => handleValueChange(status)}
              >
                <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                  {isCurrent ? <Check className="h-4 w-4" aria-hidden="true" /> : null}
                </span>
                <OrganizationOpportunityStatusLabel status={status} />
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
};

export const OrganizationOpportunityStatusDialog = ({
  pendingAction,
  onCancel,
  onConfirm,
  isSubmitting,
}) => {
  if (!pendingAction) return null;
  const { action, opportunity } = pendingAction;
  const isClose = action === 'close';
  const applicationsCount = Number(opportunity.applications_count || 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/50 px-4 py-6">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl" role="dialog" aria-modal="true">
        <h2 className="text-lg font-semibold text-neutral-950">
          {isClose ? 'Close this opportunity?' : 'Suspend this opportunity?'}
        </h2>
        <p className="mt-3 break-words text-sm leading-6 text-neutral-700">
          &quot;{opportunity.title}&quot; {isClose
            ? 'will be removed from publication. You can activate or suspend it later from your dashboard. Applications and audit history will be preserved.'
            : 'will no longer be visible to candidates. You can activate it again at any time from your dashboard.'}
        </p>
        {isClose && applicationsCount > 0 ? (
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
            This opportunity has {applicationsCount} application{applicationsCount === 1 ? '' : 's'}.
            They will be preserved but no new applications will be accepted.
          </p>
        ) : null}
        <div className="mt-6 flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            type="button"
            className={isClose
              ? 'bg-red-700 text-white hover:bg-red-800'
              : 'bg-amber-600 text-white hover:bg-amber-700'}
            onClick={onConfirm}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Saving...' : isClose ? 'Close opportunity' : 'Suspend opportunity'}
          </Button>
        </div>
      </div>
    </div>
  );
};

