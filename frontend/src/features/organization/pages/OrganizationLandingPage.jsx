import { Link } from 'react-router-dom';
import { Button } from '../../../components/ui/button.jsx';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarClock,
  Megaphone,
  Users,
} from 'lucide-react';
import {
  getPostAuthRedirectPath,
  isOrganizationAccount,
  ORGANIZATION_LOGIN_PATH,
} from '../organizationFlow.js';

// Image de fond professionnelle
const HERO_BG_IMAGE =
  'https://images.pexels.com/photos/3184418/pexels-photo-3184418.jpeg?auto=compress&cs=tinysrgb&w=1600';

const opportunityTypes = [
  { label: 'Jobs', icon: BriefcaseBusiness },
  { label: 'Internships', icon: Users },
  { label: 'Seasonal jobs', icon: CalendarClock },
];

const OrganizationLandingPage = () => {
  const { isAuthenticated, loading, user } = useAuth();
  const hasResolvedAuth = !loading || Boolean(user);
  const organizationPath =
    hasResolvedAuth && isAuthenticated
      ? getPostAuthRedirectPath({ user, organizationIntent: true })
      : ORGANIZATION_LOGIN_PATH;
  const isOrganization = isOrganizationAccount(user);
  const organizationActionLabel = isOrganization ? 'Organization dashboard' : 'Post an opportunity';

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center">
              <Link to="/" className="flex items-center gap-2">
              <span className="text-xl font-bold text-neutral-900">BidWise</span>
              <span className="rounded-md bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600">
                For Organizations
              </span>
            </Link>
              
            </div>
            <div className="flex items-center gap-4">
              {!isAuthenticated ? (
                <Link
                  to={ORGANIZATION_LOGIN_PATH}
                  className="text-sm font-medium text-neutral-600 hover:text-neutral-900"
                >
                  Sign in
                </Link>
              ) : null}
              <Button
                asChild
                size="sm"
                className="bg-blue-600 px-5 text-sm text-white hover:bg-blue-700"
              >
                <Link to={organizationPath}>{organizationActionLabel}</Link>
              </Button>
              <Link
                to="/opportunities"
                className="hidden text-sm text-neutral-600 hover:text-neutral-900 sm:inline-block"
              >
                For candidates →
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative bg-neutral-900">
        {/* Image de fond */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-30"
          style={{ backgroundImage: `url(${HERO_BG_IMAGE})` }}
        />
        
        {/* Overlay */}
        <div className="absolute inset-0 bg-black/40" />

        {/* Contenu Hero */}
        <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center text-white">
            
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
              Find the talent you're looking for
            </h1>
            
            <p className="mt-4 text-xl text-white/90">
              Post opportunities and connect with qualified candidates immediately
            </p>

            {/* CTA Button unique */}
            <div className="mt-8">
              <Button
                asChild
                size="lg"
                className="bg-blue-600 px-8 py-6 text-base text-white hover:bg-blue-700"
              >
                <Link to={organizationPath}>
                  <Megaphone className="mr-2 h-5 w-5" />
                  {organizationActionLabel}
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
            </div>

           
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="border-b border-neutral-200 bg-white py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <p className="text-3xl font-bold text-neutral-900">5,000+</p>
            <p className="text-sm text-neutral-500">active candidates on BidWise</p>
            <Button
              asChild
              variant="link"
              className="mt-2 text-blue-600 hover:text-blue-700"
            >
              <Link to={organizationPath}>
                {isOrganization ? 'Go to dashboard' : 'Start hiring today'}
                <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Opportunity Types - What you can post */}
      <section className="border-b border-neutral-200 bg-white py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-6">
            <h2 className="text-xl font-semibold text-neutral-900">
              Post hiring opportunities
            </h2>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-4">
            {opportunityTypes.map(({ label, icon: Icon }) => (
              <div
                key={label}
                className="flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm text-neutral-700"
              >
                <Icon className="h-4 w-4 text-neutral-400" />
                {label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works - 3 steps */}
      <section className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-10 text-center">
            <h2 className="text-2xl font-bold text-neutral-900">
              How posting works
            </h2>
            <p className="mt-2 text-neutral-500">
              Three simple steps to start receiving applications
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            <div className="text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-lg font-bold text-blue-600">
                1
              </div>
              <h3 className="font-semibold text-neutral-900">Create your profile</h3>
              <p className="mt-1 text-sm text-neutral-500">
                Set up your organization in minutes
              </p>
            </div>
            <div className="text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-lg font-bold text-blue-600">
                2
              </div>
              <h3 className="font-semibold text-neutral-900">Post your opportunity</h3>
              <p className="mt-1 text-sm text-neutral-500">
                Add all the details and requirements
              </p>
            </div>
            <div className="text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-lg font-bold text-blue-600">
                3
              </div>
              <h3 className="font-semibold text-neutral-900">Review candidates</h3>
              <p className="mt-1 text-sm text-neutral-500">
                Manage applications from your dashboard
              </p>
            </div>
          </div>

          <div className="mt-10 text-center">
            <Button
              asChild
              className="bg-blue-600 px-8 text-white hover:bg-blue-700"
            >
              <Link to={organizationPath}>
                {organizationActionLabel}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>


      {/* Footer */}
      <footer className="bg-white py-8">
        <div className="mx-auto max-w-7xl px-4 text-center text-sm text-neutral-500 sm:px-6 lg:px-8">
          <p>&copy; 2026 BidWise. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default OrganizationLandingPage;
