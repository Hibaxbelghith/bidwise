import { forwardRef, cloneElement, isValidElement } from 'react';
import { cn } from './utils.js';

const baseClasses =
  "inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all " +
  "disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0";

const variants = {
  default: 'bg-primary text-primary-foreground hover:bg-primary/90',
  destructive: 'bg-destructive text-white hover:bg-destructive/90',
  outline: 'border bg-background text-foreground hover:bg-accent hover:text-accent-foreground',
  secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
  ghost: 'hover:bg-accent hover:text-accent-foreground',
  link: 'text-primary underline-offset-4 hover:underline',
};

const sizes = {
  default: 'h-9 px-4 py-2',
  sm: 'h-8 rounded-md px-3',
  lg: 'h-10 rounded-md px-6',
  icon: 'h-9 w-9 rounded-md',
};

export const Button = forwardRef(
  ({ asChild = false, variant = 'default', size = 'default', className, ...props }, ref) => {
    const classes = cn(
      baseClasses,
      variants[variant] || variants.default,
      sizes[size] || sizes.default,
      className
    );

    if (asChild && isValidElement(props.children)) {
      return cloneElement(props.children, {
        className: cn(props.children.props.className, classes),
      });
    }

    return <button ref={ref} className={classes} {...props} />;
  }
);

Button.displayName = 'Button';
