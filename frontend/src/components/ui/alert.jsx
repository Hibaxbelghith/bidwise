import { cn } from './utils.js';

const variants = {
  default: 'border border-neutral-200 bg-white text-neutral-900',
  destructive: 'border border-red-200 bg-red-50 text-red-700',
};

export const Alert = ({ variant = 'default', className, ...props }) => (
  <div
    role="alert"
    className={cn('rounded-md px-4 py-3 text-sm', variants[variant] || variants.default, className)}
    {...props}
  />
);

export const AlertDescription = ({ className, ...props }) => (
  <div className={cn('text-sm', className)} {...props} />
);
