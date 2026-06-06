import { Link } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';

import { Button } from '../../../components/ui/button.jsx';
import OpportunityPostLayout from '../components/OpportunityPostLayout.jsx';

const OrganizationOpportunitySubmittedPage = () => (
  <OpportunityPostLayout
    eyebrow="Publication submitted"
    title="Votre annonce est presque prête"
    description=""
    headingId="organization-opportunity-submitted-heading"
  >
    <div className="mx-auto mt-14 w-full max-w-xl">
      <div className="flex justify-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-700">
          <CheckCircle2 className="h-7 w-7" aria-hidden="true" />
        </div>
      </div>

      <div className="mt-10 text-left">
        <p className="text-base font-semibold text-neutral-950">
          Voici les prochaines étapes concernant votre offre d'emploi :
        </p>
        <ul className="mt-5 list-disc space-y-3 pl-5 text-sm leading-6 text-neutral-700">
          <li>Nous examinerons votre offre dans les prochaines heures.</li>
          <li>Vous recevrez un email lorsque votre offre d'emploi sera en ligne.</li>
        </ul>
      </div>

      <div className="mt-12 flex justify-end">
        <Button asChild className="h-11 rounded-xl bg-blue-700 px-6 text-white hover:bg-blue-800">
          <Link to="/organization/dashboard">Continuer</Link>
        </Button>
      </div>
    </div>
  </OpportunityPostLayout>
);

export default OrganizationOpportunitySubmittedPage;
