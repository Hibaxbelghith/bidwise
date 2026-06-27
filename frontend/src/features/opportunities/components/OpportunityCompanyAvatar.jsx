import { Building2 } from 'lucide-react';

import { useLanguage } from '../../../i18n/LanguageContext.jsx';
import { buildCompanyInitialsAvatar } from '../utils/opportunityFormatters.js';

const OpportunityCompanyAvatar = ({
  companyLogo,
  organizationLabel,
  containerClassName = 'relative flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-neutral-200 bg-white',
  iconClassName = 'h-5 w-5 text-neutral-400',
  imageClassName = 'absolute inset-0 h-full w-full rounded-xl bg-white object-contain',
}) => {
  const { t } = useLanguage();
  const altText = organizationLabel
    ? t('opportunities.organizationLogo', { organization: organizationLabel })
    : t('opportunities.companyLogo');

  return (
    <div className={containerClassName}>
      <Building2 className={iconClassName} />
      {companyLogo?.src ? (
        <img
          src={companyLogo.src}
          data-fallback-src={companyLogo.fallbackSrc || ''}
          alt={altText}
          className={imageClassName}
          loading="lazy"
          onError={(event) => {
            const fallbackSrc = event.currentTarget.dataset.fallbackSrc || '';
            if (fallbackSrc && event.currentTarget.src !== fallbackSrc) {
              event.currentTarget.src = fallbackSrc;
              event.currentTarget.dataset.fallbackSrc = '';
              return;
            }

            event.currentTarget.src = buildCompanyInitialsAvatar(organizationLabel);
            event.currentTarget.dataset.fallbackSrc = '';
          }}
        />
      ) : null}
    </div>
  );
};

export default OpportunityCompanyAvatar;
