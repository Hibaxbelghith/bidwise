import { cn } from './utils.js';

export const Label = ({ className, ...props }) => (
  <label
    className={cn('text-sm font-medium text-neutral-700', className)}
    {...props}
  />
);
