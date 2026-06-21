import { Link, Navigate } from 'react-router-dom';
import { BriefcaseBusiness, CalendarClock, Sprout } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import OrganizationSidebar from '../components/OrganizationSidebar.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';

const opportunityTypes = [
  {
    label: 'Job',
    description: 'Publish a full-time, part-time, contract, CIVP, or freelance job.',
    icon: BriefcaseBusiness,
    href: '/organization/post/job',
    enabled: true,
  },
  {
    label: 'Internship',
    description: 'Create internship, PFE, trainee, or early-career opportunities.',
    icon: Sprout,
    href: '/organization/post/internship',
    enabled: true,
  },
  {
    label: 'Seasonal job',
    description: 'Post temporary seasonal roles with simple availability and location details.',
    icon: CalendarClock,
    href: '/organization/post/seasonal',
    enabled: true,
  },
];

const OrganizationOpportunityPostPage = () => {
  const { user, loading } = useAuth();
  const profile = user?.organization_profile;

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-neutral-50 px-4">
        <div className="rounded-lg border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-600">
          Loading organization workspace
        </div>
      </section>
    );
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  return (
    <section className="min-h-[calc(100vh-4rem)] bg-white" aria-labelledby="choose-opportunity-type-heading">
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[286px_1fr]">
        <OrganizationSidebar activePath="/organization/post" />

        <main className="min-w-0 px-5 py-10">
          <div className="mx-auto max-w-5xl">
            <div className="text-center">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">Create opportunity</p>
              <h1 id="choose-opportunity-type-heading" className="mt-3 text-4xl font-semibold tracking-tight text-neutral-950">
                What do you want to publish?
              </h1>

            </div>

            <div className="mt-12 grid gap-5 md:grid-cols-3">
              {opportunityTypes.map((type) => {
                const Icon = type.icon;
                const card = (
                  <div
                    className={[
                      'group flex h-full flex-col rounded-2xl border bg-white p-6 text-left shadow-sm transition-all',
                      type.enabled
                        ? 'border-neutral-200 hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md'
                        : 'border-neutral-200 opacity-75',
                    ].join(' ')}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
                        <Icon className="h-6 w-6" aria-hidden="true" />
                      </div>
                    </div>
                    <h2 className="mt-6 text-xl font-semibold text-neutral-950">{type.label}</h2>
                    <p className="mt-3 flex-1 text-sm leading-6 text-neutral-600">{type.description}</p>
                    <div className="mt-6">
                      {type.enabled ? (
                        <Button className="h-10 rounded-xl bg-blue-700 text-white hover:bg-blue-800">
                          Continue
                        </Button>
                      ) : (
                        <span className="inline-flex h-10 items-center rounded-xl border border-neutral-200 px-4 text-sm font-medium text-neutral-500">
                          Next step
                        </span>
                      )}
                    </div>
                  </div>
                );

                return type.enabled ? (
                  <Link key={type.href} to={type.href} className="block">
                    {card}
                  </Link>
                ) : (
                  <div key={type.href || type.label}>{card}</div>
                );
              })}
            </div>
          </div>
        </main>
      </div>
    </section>
  );
};

export default OrganizationOpportunityPostPage;
