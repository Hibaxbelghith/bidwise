import { FIELD_CLASS } from '../opportunityPostConstants.js';

export const FieldError = ({ message }) => (
  message ? <p className="mt-2 text-sm text-red-600">{message}</p> : null
);

export const SubmitNotice = ({ message, tone = 'error' }) => {
  if (!message) return null;
  const isWarning = tone === 'warning';
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${
      isWarning
        ? 'border-amber-200 bg-amber-50 text-amber-900'
        : 'border-red-200 bg-red-50 text-red-800'
    }`}>
      <p className="font-semibold">{isWarning ? 'Publishing paused' : 'Unable to publish'}</p>
      <p className="mt-1 leading-6">{message}</p>
    </div>
  );
};

export const ErrorSummary = ({ errors, labels }) => {
  const items = Object.keys(errors || {})
    .map((key) => labels?.[key])
    .filter(Boolean);

  if (items.length === 0) return null;

  return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <p className="font-semibold">These items need your attention before continuing.</p>
      <ul className="mt-2 list-disc space-y-1 pl-5">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
};

export const FieldBlock = ({ children, className = '' }) => (
  <section className={`border-t border-neutral-200 pt-8 ${className}`}>
    {children}
  </section>
);

export const fieldClassName = (hasError) => `${FIELD_CLASS} ${hasError ? 'border-red-300' : ''}`;
