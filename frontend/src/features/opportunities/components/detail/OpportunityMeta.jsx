import {
  Briefcase,
  Building2,
  Calendar,
  GraduationCap,
  MapPin,
  Wallet,
} from 'lucide-react';

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
}) => (
  <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    {isProject ? (
      <>
        <KeyInfoCard icon={<Building2 className="h-3.5 w-3.5" />} label="Acheteur" value={organizationLabel} />
        <KeyInfoCard icon={<MapPin className="h-3.5 w-3.5" />} label="Région" value={projectRegionLabel} />
        <KeyInfoCard
          icon={<Briefcase className="h-3.5 w-3.5" />}
          label="Procédure"
          value={projectProcedureLabel}
        />
        <KeyInfoCard
          icon={<Wallet className="h-3.5 w-3.5" />}
          label="Financement"
          value={projectFinancementLabel}
        />
      </>
    ) : (
      <>
        <KeyInfoCard icon={<Wallet className="h-3.5 w-3.5" />} label="Salary" value={salaryLabel} />
        <KeyInfoCard icon={<MapPin className="h-3.5 w-3.5" />} label="Location" value={locationLabel} />
        <KeyInfoCard icon={<Briefcase className="h-3.5 w-3.5" />} label="Contract" value={contractLabel} />
        <KeyInfoCard
          icon={<Calendar className="h-3.5 w-3.5" />}
          label="Availability"
          value={availabilityLabel}
        />
        <KeyInfoCard
          icon={<GraduationCap className="h-3.5 w-3.5" />}
          label="Experience"
          value={experienceLabel}
        />
        <KeyInfoCard
          icon={<GraduationCap className="h-3.5 w-3.5" />}
          label="Education"
          value={educationLabel}
        />
      </>
    )}
  </section>
);

export default OpportunityMeta;
