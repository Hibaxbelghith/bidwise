import { useEffect, useRef, useState } from 'react';
import { ExternalLink, Eye, MoreHorizontal, Pencil } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '../../../components/ui/button.jsx';
import { organizationOpportunityEditPath } from '../hooks/useOrganizationOpportunityEdit.js';
import { useLanguage } from '../../../i18n/LanguageContext.jsx';

const MENU_ITEM_CLASS =
  'flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm text-neutral-700 transition hover:bg-neutral-100 hover:text-neutral-950';

const OrganizationOpportunityActionsMenu = ({ opportunity, editable }) => {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const [opensUpward, setOpensUpward] = useState(false);
  const menuRef = useRef(null);
  const isPublic = opportunity.status === 'ACTIVE';
  const editPath = editable ? organizationOpportunityEditPath(opportunity) : null;

  useEffect(() => {
    if (!isOpen) return undefined;

    const closeOnOutsideClick = (event) => {
      if (!menuRef.current?.contains(event.target)) setIsOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setIsOpen(false);
    };

    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [isOpen]);

  const toggleMenu = () => {
    if (!isOpen) {
      const triggerBounds = menuRef.current?.getBoundingClientRect();
      const estimatedMenuHeight = 170;
      const availableBelow = window.innerHeight - (triggerBounds?.bottom || 0);
      setOpensUpward(availableBelow < estimatedMenuHeight);
    }
    setIsOpen((current) => !current);
  };

  return (
    <div ref={menuRef} className={`relative inline-flex ${isOpen ? 'z-50' : ''}`}>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        title={t('organization.opportunityActions')}
        aria-label={t('organization.actionsForOpportunity', { title: opportunity.title })}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={toggleMenu}
      >
        <MoreHorizontal className="h-5 w-5" aria-hidden="true" />
      </Button>

      {isOpen ? (
        <div
          role="menu"
          className={`absolute right-0 z-50 w-52 rounded-md border border-neutral-200 bg-white p-1.5 shadow-xl ${
            opensUpward ? 'bottom-full mb-1' : 'top-full mt-1'
          }`}
        >
          <Link
            className={MENU_ITEM_CLASS}
            to={`/organization/opportunities/${opportunity.id}`}
            role="menuitem"
            onClick={() => setIsOpen(false)}
          >
            <Eye className="h-4 w-4" aria-hidden="true" />
            {t('admin.viewDetails')}
          </Link>

          {editPath ? (
            <Link className={MENU_ITEM_CLASS} to={editPath} role="menuitem" onClick={() => setIsOpen(false)}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              {t('organization.edit')}
            </Link>
          ) : (
            <span className={`${MENU_ITEM_CLASS} cursor-not-allowed opacity-50`}>
              <Pencil className="h-4 w-4" aria-hidden="true" />
              {t('organization.edit')}
            </span>
          )}

          {isPublic ? (
            <Link
              className={MENU_ITEM_CLASS}
              to={`/opportunities/${opportunity.id}`}
              role="menuitem"
              onClick={() => setIsOpen(false)}
            >
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              {t('organization.viewOnBidWise')}
            </Link>
          ) : (
            <span className={`${MENU_ITEM_CLASS} cursor-not-allowed opacity-50`} title={t('organization.notPubliclyAvailable')}>
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              {t('organization.viewOnBidWise')}
            </span>
          )}
        </div>
      ) : null}
    </div>
  );
};

export default OrganizationOpportunityActionsMenu;
