import { ChevronLeft, ChevronRight } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { useLanguage } from '../../../i18n/LanguageContext.jsx';

const OrganizationOpportunitiesPagination = ({ page, pageSize, total, onPageChange }) => {
  const { t } = useLanguage();
  const totalPages = Math.max(Math.ceil(total / pageSize), 1);
  const firstItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastItem = Math.min(page * pageSize, total);

  if (total <= pageSize) return null;

  return (
    <div className="flex flex-col gap-3 border-t border-neutral-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-neutral-500">
        {t('organization.showingRange', { first: firstItem, last: lastItem, total })}
      </p>
      <div className="flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={page === 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          {t('admin.previous')}
        </Button>
        <span className="min-w-24 text-center text-sm font-medium text-neutral-700">
          {t('organization.pageOf', { page, totalPages })}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={page === totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          {t('admin.next')}
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
};

export default OrganizationOpportunitiesPagination;
