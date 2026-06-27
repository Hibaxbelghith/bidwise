import {
  Briefcase,
  Building2,
  Calendar,
  GraduationCap,
  MapPin,
  Wallet,
} from 'lucide-react';

import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import KeyInfoCard from './KeyInfoCard.jsx';

const OpportunityMeta = ({
  isProject,
  organizationLabel,
  projectRegionLabel,
  projectProcedureLabel,
  projectFinancementLabel,
  salaryLabel,
  locationLabel,
  contractLabel,
  availabilityLabel,
  experienceLabel,
  educationLabel,
}) => {
  const { t } = useLanguage();

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {isProject ? (
        <>
          <KeyInfoCard icon={<Building2 className="h-3.5 w-3.5" />} label={t('opportunities.detail.buyer')} value={organizationLabel} />
          <KeyInfoCard icon={<MapPin className="h-3.5 w-3.5" />} label={t('opportunities.detail.region')} value={projectRegionLabel} />
          <KeyInfoCard
            icon={<Briefcase className="h-3.5 w-3.5" />}
            label={t('opportunities.detail.procedure')}
            value={projectProcedureLabel}
          />
          <KeyInfoCard
            icon={<Wallet className="h-3.5 w-3.5" />}
            label={t('opportunities.detail.financing')}
            value={projectFinancementLabel}
          />
        </>
      ) : (
        <>
          <KeyInfoCard icon={<Wallet className="h-3.5 w-3.5" />} label={t('opportunities.detail.salary')} value={salaryLabel} />
          <KeyInfoCard icon={<MapPin className="h-3.5 w-3.5" />} label={t('opportunities.detail.location')} value={locationLabel} />
          <KeyInfoCard icon={<Briefcase className="h-3.5 w-3.5" />} label={t('opportunities.detail.contract')} value={contractLabel} />
          <KeyInfoCard
            icon={<Calendar className="h-3.5 w-3.5" />}
            label={t('opportunities.detail.availability')}
            value={availabilityLabel}
          />
          <KeyInfoCard
            icon={<GraduationCap className="h-3.5 w-3.5" />}
            label={t('opportunities.detail.experience')}
            value={experienceLabel}
          />
          <KeyInfoCard
            icon={<GraduationCap className="h-3.5 w-3.5" />}
            label={t('opportunities.detail.education')}
            value={educationLabel}
          />
        </>
      )}
    </section>
  );
};

export default OpportunityMeta;
