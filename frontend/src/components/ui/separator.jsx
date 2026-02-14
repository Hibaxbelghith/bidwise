import { cn } from './utils.js';

export const Separator = ({ className, ...props }) => (
  <div
    role="separator"
    className={cn('h-px w-full bg-neutral-200', className)}
    {...props}
  />
);
