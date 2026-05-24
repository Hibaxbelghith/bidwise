import { memo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { Label } from '../../../components/ui/label.jsx';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../../components/ui/select.jsx';

const AdminUsersPagination = ({
  page,
  totalPages,
  pageSize,
  pageSizeOptions,
  hasNext,
  hasPrevious,
  isLoading,
  onChangePage,
  onChangePageSize,
}) => (
  <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
      <p className="text-sm text-neutral-500">
        Page {page} of {totalPages}
      </p>
      <div className="flex items-center gap-2">
        <Label htmlFor="admin-user-page-size" className="text-xs text-neutral-500">Rows</Label>
        <div className="w-28">
          <Select
            value={String(pageSize)}
            onValueChange={(value) => onChangePageSize(value)}
          >
            <SelectTrigger id="admin-user-page-size" className="h-9" aria-label="Rows per page">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
    <div className="flex gap-2">
      <Button
        type="button"
        variant="outline"
        aria-label="Previous page"
        disabled={!hasPrevious || isLoading}
        onClick={() => onChangePage(Math.max(page - 1, 1))}
      >
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        Prev
      </Button>
      <Button
        type="button"
        variant="outline"
        aria-label="Next page"
        disabled={!hasNext || isLoading}
        onClick={() => onChangePage(page + 1)}
      >
        Next
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    </div>
  </div>
);

export default memo(AdminUsersPagination);
