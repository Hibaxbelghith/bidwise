import { forwardRef } from 'react';
import { cn } from './utils.js';

export const Checkbox = forwardRef(({ className, ...props }, ref) => (
  <input
    ref={ref}
    type="checkbox"
    className={cn(
      'h-4 w-4 rounded border border-neutral-300 text-blue-600 focus-visible:outline-none ' +
        'focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
      className
    )}
    {...props}
  />
));

Checkbox.displayName = 'Checkbox';
