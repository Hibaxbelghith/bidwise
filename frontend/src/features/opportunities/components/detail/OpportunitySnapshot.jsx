import { hasDisplayValue } from '../../utils/opportunityHelpers.js';

const OpportunitySnapshot = ({
  sourceName,
  isProject,
  typeLabel,
  projectRegionLabel,
  projectProcedureLabel,
  projectFinancementLabel,
  projectTypeCommandeLabel,
  projectCautionLabel,
  organizationLabel,
  contractLabel,
  availabilityLabel,
  experienceLabel,
  educationLabel,
  languagesLabel,
}) => {
  return (
    <dl className="space-y-3 text-sm">
      <div>
        <dt className="text-neutral-500">Source</dt>
        <dd className="font-medium text-neutral-900">{sourceName}</dd>
      </div>
      <div>
        <dt className="text-neutral-500">Type</dt>
        <dd className="font-medium text-neutral-900">{typeLabel}</dd>
      </div>
      {isProject ? (
        <>
          <div>
            <dt className="text-neutral-500">Acheteur</dt>
            <dd className="font-medium text-neutral-900">{organizationLabel}</dd>
          </div>
          <div>
            <dt className="text-neutral-500">Région</dt>
            <dd className="font-medium text-neutral-900">{projectRegionLabel}</dd>
          </div>
          <div>
            <dt className="text-neutral-500">Procédure</dt>
            <dd className="font-medium text-neutral-900">{projectProcedureLabel}</dd>
          </div>
          <div>
            <dt className="text-neutral-500">Financement</dt>
            <dd className="font-medium text-neutral-900">{projectFinancementLabel}</dd>
          </div>
          <div>
            <dt className="text-neutral-500">Type commande</dt>
            <dd className="font-medium text-neutral-900">{projectTypeCommandeLabel}</dd>
          </div>
          <div>
            <dt className="text-neutral-500">Caution</dt>
            <dd className="font-medium text-neutral-900">{projectCautionLabel}</dd>
          </div>
        </>
      ) : (
        <>
          {hasDisplayValue(contractLabel) ? (
            <div>
              <dt className="text-neutral-500">Contract</dt>
              <dd className="font-medium text-neutral-900">{contractLabel}</dd>
            </div>
          ) : null}
          {hasDisplayValue(availabilityLabel) ? (
            <div>
              <dt className="text-neutral-500">Availability</dt>
              <dd className="font-medium text-neutral-900">{availabilityLabel}</dd>
            </div>
          ) : null}
          {hasDisplayValue(experienceLabel) ? (
            <div>
              <dt className="text-neutral-500">Experience</dt>
              <dd className="font-medium text-neutral-900">{experienceLabel}</dd>
            </div>
          ) : null}
          {hasDisplayValue(educationLabel) ? (
            <div>
              <dt className="text-neutral-500">Education</dt>
              <dd className="font-medium text-neutral-900">{educationLabel}</dd>
            </div>
          ) : null}
          {hasDisplayValue(languagesLabel) ? (
            <div>
              <dt className="text-neutral-500">Languages</dt>
              <dd className="font-medium text-neutral-900">{languagesLabel}</dd>
            </div>
          ) : null}
        </>
      )}
    </dl>
  );
};

export default OpportunitySnapshot;
