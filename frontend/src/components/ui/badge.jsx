import { cn } from './utils.js';

const variants = {
  default: 'bg-blue-600 text-white',
  secondary: 'bg-neutral-100 text-neutral-800',
  outline: 'border border-neutral-200 text-neutral-700',
};

export const Badge = ({ variant = 'default', className, ...props }) => (
  <span
    className={cn(
      'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium',
      variants[variant] || variants.default,
      className
    )}
    {...props}
  />
);
