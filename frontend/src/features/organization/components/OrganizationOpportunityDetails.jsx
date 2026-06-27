import { BriefcaseBusiness, CalendarDays, FileText, MapPin, Users } from 'lucide-react';

import { Badge } from '../../../components/ui/badge.jsx';
import { useLanguage } from '../../../i18n/LanguageContext.jsx';
import {
  ORGANIZATION_OPPORTUNITY_STATUS_LABELS,
  ORGANIZATION_OPPORTUNITY_TYPE_LABELS,
  formatOrganizationOpportunityDate,
  formatOrganizationOpportunityFieldLabel,
} from '../utils/organizationOpportunityFormatters.js';
import {
  getOrganizationOpportunityStatusLabel,
  getOrganizationOpportunityTypeLabel,
  getOrganizationOpportunityValueLabel,
} from '../utils/organizationLabelUtils.js';

const DetailItem = ({ label, value, t }) => (
  <div className="min-w-0 border-b border-neutral-100 py-3">
    <dt className="text-xs font-semibold uppercase text-neutral-500">{label}</dt>
    <dd className="mt-1 break-words text-sm text-neutral-900">
      {getOrganizationOpportunityValueLabel(value, t)}
    </dd>
  </div>
);

const DetailGrid = ({ children }) => (
  <dl className="grid gap-x-8 sm:grid-cols-2 xl:grid-cols-3">{children}</dl>
);

const DetailSection = ({ title, children }) => (
  <section className="border-t border-neutral-200 py-7">
    <h2 className="text-lg font-semibold text-neutral-950">{title}</h2>
    <div className="mt-4">{children}</div>
  </section>
);

const GenericDetails = ({ details, excludedKeys = [], t }) => {
  const entries = Object.entries(details || {}).filter(([key, value]) => (
    !excludedKeys.includes(key)
    && !key.toLowerCase().endsWith('_url')
    && key !== 'has_pdf'
    && !Array.isArray(value)
    && value !== null
    && value !== undefined
    && value !== ''
  ));

  if (!entries.length) return null;

  return (
    <DetailGrid>
      {entries.map(([key, value]) => (
        <DetailItem
          key={key}
          label={formatOrganizationOpportunityFieldLabel(key)}
          value={value}
          t={t}
        />
      ))}
    </DetailGrid>
  );
};

const TenderDetails = ({ details, t }) => {
  const lots = Array.isArray(details?.lots) ? details.lots : [];
  const documents = Array.isArray(details?.documents) ? details.documents : [];

  return (
    <DetailSection title={t('organization.tenderDetails')}>
      <GenericDetails details={details} excludedKeys={['lots', 'documents']} t={t} />

      {lots.length ? (
        <div className="mt-7">
          <h3 className="text-sm font-semibold text-neutral-950">
            Lots ({lots.length})
          </h3>
          <div className="mt-3 divide-y divide-neutral-200 border-y border-neutral-200">
            {lots.map((lot, index) => (
              <div key={`${lot.title || lot.object || 'lot'}-${index}`} className="py-5">
                <p className="font-semibold text-neutral-950">
                  {lot.title || `Lot ${index + 1}`}
                </p>
                <GenericDetails details={lot} excludedKeys={['title']} />
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {documents.length ? (
        <div className="mt-7">
          <h3 className="text-sm font-semibold text-neutral-950">
            Documents ({documents.length})
          </h3>
          <div className="mt-3 divide-y divide-neutral-200 border-y border-neutral-200">
            {documents.map((document, index) => (
              <div
                key={`${document.url || document.label || 'document'}-${index}`}
                className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="break-words text-sm font-medium text-neutral-950">
                    {document.label || document.name || `Document ${index + 1}`}
                  </p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {getOrganizationOpportunityValueLabel(document.type, t)}
                  </p>
                </div>
                {document.url ? (
                  <a
                    href={document.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-semibold text-blue-700 hover:text-blue-800"
                  >
                    {t('organization.openDocument')}
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </DetailSection>
  );
};

const OrganizationOpportunityDetails = ({ opportunity }) => {
  const { language, t } = useLanguage();
  const experience = opportunity.experience_min !== null || opportunity.experience_max !== null
    ? t('organization.experienceYearsRange', {
      min: opportunity.experience_min ?? 0,
      max: opportunity.experience_max ?? t('organization.notSet'),
    })
    : t('organization.notSet');

  return (
    <main className="px-5 py-6 sm:px-8">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <Users className="h-5 w-5 text-blue-700" aria-hidden="true" />
          <p className="mt-3 text-2xl font-semibold text-neutral-950">
            {opportunity.applications_count || 0}
          </p>
          <p className="mt-1 text-sm text-neutral-500">{t('organization.applicationsReceived')}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <BriefcaseBusiness className="h-5 w-5 text-blue-700" aria-hidden="true" />
          <p className="mt-3 text-base font-semibold text-neutral-950">
            {getOrganizationOpportunityStatusLabel(
              opportunity.status,
              t,
              ORGANIZATION_OPPORTUNITY_STATUS_LABELS[opportunity.status] || opportunity.status,
            )}
          </p>
          <p className="mt-1 text-sm text-neutral-500">{t('organization.publicationStatus')}</p>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <CalendarDays className="h-5 w-5 text-blue-700" aria-hidden="true" />
          <p className="mt-3 text-base font-semibold text-neutral-950">
            {formatOrganizationOpportunityDate(opportunity.deadline, {}, language)}
          </p>
          <p className="mt-1 text-sm text-neutral-500">{t('organization.applicationDeadline')}</p>
        </div>
      </div>

      <div className="mt-6 bg-white px-5 sm:px-7">
        <DetailSection title={t('organization.opportunitySummary')}>
          <DetailGrid>
            <DetailItem
              label={t('organization.type')}
              value={getOrganizationOpportunityTypeLabel(
                opportunity.type,
                t,
                ORGANIZATION_OPPORTUNITY_TYPE_LABELS[opportunity.type] || opportunity.type,
              )}
              t={t}
            />
            <DetailItem label={t('organization.location')} value={opportunity.location} t={t} />
            <DetailItem
              label={t('admin.published')}
              value={formatOrganizationOpportunityDate(opportunity.published_at, {}, language)}
              t={t}
            />
            <DetailItem
              label={t('organization.lastUpdated')}
              value={formatOrganizationOpportunityDate(opportunity.updated_at, {
                hour: '2-digit',
                minute: '2-digit',
              }, language)}
              t={t}
            />
            <DetailItem label={t('organization.contract')} value={opportunity.contract} t={t} />
            <DetailItem label={t('organization.workArrangement')} value={opportunity.availability} t={t} />
            <DetailItem label={t('organization.experience')} value={experience} t={t} />
            <DetailItem label={t('organization.educationLevel')} value={opportunity.education_level} t={t} />
            <DetailItem label={t('organization.salary')} value={opportunity.salary} t={t} />
          </DetailGrid>
        </DetailSection>

        {opportunity.skills?.length ? (
          <DetailSection title={t('profile.skills')}>
            <div className="flex flex-wrap gap-2">
              {opportunity.skills.map((skill) => (
                <Badge key={skill} variant="secondary">{skill}</Badge>
              ))}
            </div>
          </DetailSection>
        ) : null}

        <DetailSection title={t('organization.description')}>
          <div className="flex gap-3">
            <FileText className="mt-0.5 h-5 w-5 shrink-0 text-neutral-400" aria-hidden="true" />
            <p className="whitespace-pre-wrap break-words text-sm leading-7 text-neutral-700">
              {opportunity.description || t('organization.noDescriptionProvided')}
            </p>
          </div>
        </DetailSection>

        {opportunity.type === 'STAGE' && opportunity.internship_details ? (
          <DetailSection title={t('organization.internshipDetails')}>
            <GenericDetails details={opportunity.internship_details} t={t} />
          </DetailSection>
        ) : null}

        {opportunity.type === 'SAISONNIER' && opportunity.seasonal_details ? (
          <DetailSection title={t('organization.seasonalJobDetails')}>
            <GenericDetails details={opportunity.seasonal_details} t={t} />
          </DetailSection>
        ) : null}

        {opportunity.type === 'PROJET' && opportunity.project_details ? (
          <TenderDetails details={opportunity.project_details} t={t} />
        ) : null}

        <div className="flex items-center gap-2 border-t border-neutral-200 py-6 text-sm text-neutral-500">
          <MapPin className="h-4 w-4" aria-hidden="true" />
          {opportunity.location || t('organization.locationNotSet')}
        </div>
      </div>
    </main>
  );
};

export default OrganizationOpportunityDetails;
