import { cn } from './utils.js';

export const Table = ({ className, containerClassName, ...props }) => (
  <div data-slot="table-container" className={cn('relative w-full overflow-x-auto', containerClassName)}>
    <table data-slot="table" className={cn('w-full caption-bottom text-sm', className)} {...props} />
  </div>
);

export const TableHeader = ({ className, ...props }) => (
  <thead data-slot="table-header" className={cn('[&_tr]:border-b', className)} {...props} />
);

export const TableBody = ({ className, ...props }) => (
  <tbody data-slot="table-body" className={cn('[&_tr:last-child]:border-0', className)} {...props} />
);

export const TableFooter = ({ className, ...props }) => (
  <tfoot
    data-slot="table-footer"
    className={cn('bg-muted/50 border-t font-medium [&>tr]:last:border-b-0', className)}
    {...props}
  />
);

export const TableRow = ({ className, ...props }) => (
  <tr
    data-slot="table-row"
    className={cn('hover:bg-muted/50 data-[state=selected]:bg-muted border-b transition-colors', className)}
    {...props}
  />
);

export const TableHead = ({ className, ...props }) => (
  <th
    data-slot="table-head"
    className={cn(
      'text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap ' +
        '[&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]',
      className
    )}
    {...props}
  />
);

export const TableCell = ({ className, ...props }) => (
  <td
    data-slot="table-cell"
    className={cn(
      'p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]',
      className
    )}
    {...props}
  />
);

export const TableCaption = ({ className, ...props }) => (
  <caption data-slot="table-caption" className={cn('text-muted-foreground mt-4 text-sm', className)} {...props} />
);
