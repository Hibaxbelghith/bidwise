import * as Dialog from '@radix-ui/react-dialog';
import { Briefcase, Check, Clock3, ExternalLink, Loader2, X } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';

const ExternalApplicationFollowUpDialog = ({
  open,
  onOpenChange,
  opportunityTitle,
  organizationLabel,
  sourceUrl,
  isBusy,
  error,
  onConfirmApplied,
  onNotYet,
  onRemindLater,
}) => (
  <Dialog.Root open={open} onOpenChange={(nextOpen) => !isBusy && onOpenChange(nextOpen)}>
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-[82] bg-black/40" />
      <Dialog.Content className="fixed inset-x-0 bottom-0 z-[83] max-h-[90vh] overflow-y-auto rounded-t-xl bg-white shadow-xl sm:inset-auto sm:left-1/2 sm:top-1/2 sm:w-[min(92vw,480px)] sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl">
        <div className="border-b border-neutral-100 px-5 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <Dialog.Title className="text-lg font-semibold text-neutral-950">
                Did you apply?
              </Dialog.Title>
              <div className="mt-2 rounded-xl border border-blue-100 bg-blue-50/60 px-3 py-3">
                <p className="text-sm font-medium text-neutral-900">{opportunityTitle}</p>
                {organizationLabel ? (
                  <p className="mt-1 text-sm text-neutral-600">{organizationLabel}</p>
                ) : null}
              </div>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
                disabled={isBusy}
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>
        </div>

        <div className="space-y-4 p-5">
          <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3">
            <div className="flex items-start gap-3">
              <Briefcase className="mt-0.5 h-4 w-4 text-blue-600" />
              <p className="text-sm leading-6 text-neutral-700">
                BidWise opened the employer page in a new tab. Tell us whether you completed the application so we can keep your dashboard up to date.
              </p>
            </div>
          </div>

          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </div>
          ) : null}

          <div className="grid gap-3">
            <Button
              type="button"
              onClick={onConfirmApplied}
              disabled={isBusy}
              className="h-11 bg-blue-600 hover:bg-blue-700"
            >
              {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Yes, I applied
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={onNotYet}
              disabled={isBusy}
              className="h-11"
            >
              <ExternalLink className="h-4 w-4" />
              No, not yet
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={onRemindLater}
              disabled={isBusy}
              className="h-11"
            >
              <Clock3 className="h-4 w-4" />
              Remind me later
            </Button>
          </div>

          {sourceUrl ? (
            <div className="border-t border-neutral-100 pt-4">
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
              >
                Reopen employer page
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          ) : null}
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>
);

export default ExternalApplicationFollowUpDialog;
