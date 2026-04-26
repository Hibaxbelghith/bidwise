import { Lock } from 'lucide-react';

const LockPreviewCard = ({ title, body }) => (
  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
    <p className="mb-1 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
      <Lock className="h-3.5 w-3.5" />
      {title}
    </p>
    <p className="text-sm leading-6 text-neutral-700">{body}</p>
  </div>
);

export default LockPreviewCard;
