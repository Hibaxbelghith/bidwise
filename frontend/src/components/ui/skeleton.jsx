import { cn } from './utils.js';

const Skeleton = ({ className }) => (
  <div
    className={cn('animate-pulse rounded-md bg-neutral-200', className)}
    aria-hidden="true"
  />
);

export default Skeleton;
