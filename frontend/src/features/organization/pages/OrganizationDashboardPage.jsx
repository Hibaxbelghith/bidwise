import { Link, Navigate } from 'react-router-dom';
import { Building2, CheckCircle2, FilePlus2, Loader2, Settings } from 'lucide-react';
import { Button } from '../../../components/ui/button.jsx';
import { Card, CardContent } from '../../../components/ui/card.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ORGANIZATION_CREATE_ACCOUNT_PATH,
  isOrganizationProfileComplete,
} from '../organizationFlow.js';

const OrganizationDashboardPage = () => {
  const { user, loading } = useAuth();
  const profile = user?.organization_profile;

  if (loading) {
    return (
      <section className="flex min-h-[70vh] items-center justify-center bg-neutral-50 px-4">
        <div className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-600">
          <Loader2 className="h-4 w-4 animate-spin text-emerald-700" aria-hidden="true" />
          Loading organization workspace
        </div>
      </section>
    );
  }

  if (!isOrganizationProfileComplete(profile)) {
    return <Navigate to={ORGANIZATION_CREATE_ACCOUNT_PATH} replace />;
  }

  return (
    <section className="min-h-[70vh] bg-neutral-50 py-10" aria-labelledby="organization-dashboard-heading">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Organization workspace</p>
            <h1 id="organization-dashboard-heading" className="mt-2 text-3xl font-semibold text-neutral-950">
              {profile.organization_name}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
              Your organization account is ready. Opportunity posting and promoter tools can now build on this profile foundation.
            </p>
          </div>

          <Button className="h-10 rounded-md bg-neutral-950 text-white hover:bg-neutral-800" disabled>
            <FilePlus2 className="h-4 w-4" aria-hidden="true" />
            Post an opportunity
          </Button>
        </div>

        <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <Card className="rounded-lg border-neutral-200 bg-white">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 items-center justify-center rounded-md bg-emerald-50 text-emerald-700">
                  <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-neutral-950">Profile completed</h2>
                  <p className="mt-2 text-sm leading-6 text-neutral-600">
                    BidWise has the basic organization and contact details needed before posting workflows are enabled.
                  </p>
                  <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Contact</dt>
                      <dd className="mt-1 text-sm text-neutral-900">
                        {profile.first_name} {profile.last_name}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Phone</dt>
                      <dd className="mt-1 text-sm text-neutral-900">{profile.phone}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Type</dt>
                      <dd className="mt-1 text-sm capitalize text-neutral-900">{profile.organization_type}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Website</dt>
                      <dd className="mt-1 text-sm text-neutral-900">
                        {profile.website ? (
                          <a href={profile.website} className="text-emerald-700 hover:text-emerald-800" target="_blank" rel="noreferrer">
                            {profile.website}
                          </a>
                        ) : (
                          'Not provided'
                        )}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-lg border-neutral-200 bg-white">
            <CardContent className="p-6">
              <div className="flex h-11 w-11 items-center justify-center rounded-md bg-neutral-100 text-neutral-800">
                <Building2 className="h-5 w-5" aria-hidden="true" />
              </div>
              <h2 className="mt-5 text-lg font-semibold text-neutral-950">Next up</h2>
              <p className="mt-2 text-sm leading-6 text-neutral-600">
                The first dashboard is intentionally simple while posting, applicant review, and analytics are added.
              </p>
              <Button asChild variant="outline" className="mt-6 h-10 rounded-md">
                <Link to="/organizations">
                  <Settings className="h-4 w-4" aria-hidden="true" />
                  View organization entry
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
};

export default OrganizationDashboardPage;
