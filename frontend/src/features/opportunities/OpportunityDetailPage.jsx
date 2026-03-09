import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Button } from '../../components/ui/button.jsx';
import { Badge } from '../../components/ui/badge.jsx';
import { Separator } from '../../components/ui/separator.jsx';
import {
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  Building2,
  Calendar,
  Clock,
  DollarSign,
  ExternalLink,
  MapPin,
  Share2,
} from 'lucide-react';

const OpportunityDetail = () => {
  const { id } = useParams();
  const [isSaved, setIsSaved] = useState(false);

  const opportunity = {
    id: id || '1',
    title: 'Senior Software Engineer',
    organization: 'TechCorp Inc.',
    organizationLogo: 'https://via.placeholder.com/80',
    type: 'Job Offer',
    location: 'Remote',
    locationType: 'Fully Remote',
    salary: '$120,000 - $160,000',
    postedDate: 'February 8, 2026',
    deadline: 'March 15, 2026',
    employmentType: 'Full-time',
    experience: '5+ years',
    tags: ['React', 'Node.js', 'TypeScript', 'PostgreSQL', 'AWS'],
    description:
      "We're looking for an experienced Senior Software Engineer to join our platform team. You'll be working on building and scaling our core product used by thousands of companies worldwide.",
    responsibilities: [
      'Design and implement new features for our platform',
      'Lead technical discussions and architectural decisions',
      'Mentor junior engineers and conduct code reviews',
      'Collaborate with product and design teams',
      'Optimize application performance and scalability',
    ],
    requirements: [
      '5+ years of professional software development experience',
      'Strong expertise in React, Node.js, and TypeScript',
      'Experience with PostgreSQL and database design',
      'Familiarity with AWS services and cloud architecture',
      'Excellent problem-solving and communication skills',
    ],
    benefits: [
      'Competitive salary and equity package',
      'Health, dental, and vision insurance',
      '401(k) matching',
      'Unlimited PTO',
      'Remote work flexibility',
      'Professional development budget',
    ],
    about:
      "TechCorp Inc. is a leading software company building tools that empower teams to work more efficiently. Founded in 2015, we've grown to serve over 10,000 customers across 50 countries.",
    applicationUrl: 'https://example.com/apply',
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="border-b border-neutral-200 bg-neutral-50">
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
          <Link
            to="/opportunities"
            className="mb-6 inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to opportunities
          </Link>

          <div className="flex items-start justify-between gap-6">
            <div className="flex flex-1 gap-6">
              <div className="flex h-20 w-20 flex-shrink-0 items-center justify-center rounded-lg border border-neutral-200 bg-white">
                <Building2 className="h-10 w-10 text-neutral-400" />
              </div>
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-3">
                  <h1 className="text-3xl font-bold text-neutral-900">{opportunity.title}</h1>
                  <Badge>{opportunity.type}</Badge>
                </div>
                <p className="mb-4 text-xl text-neutral-600">{opportunity.organization}</p>
                <div className="flex flex-wrap gap-4 text-neutral-600">
                  <span className="flex items-center gap-2">
                    <MapPin className="h-4 w-4" />
                    {opportunity.location}
                  </span>
                  <span className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4" />
                    {opportunity.salary}
                  </span>
                  <span className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    {opportunity.employmentType}
                  </span>
                  <span className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Posted {opportunity.postedDate}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex flex-shrink-0 gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setIsSaved((prev) => !prev)}
              >
                {isSaved ? (
                  <BookmarkCheck className="h-5 w-5 text-blue-600" />
                ) : (
                  <Bookmark className="h-5 w-5" />
                )}
              </Button>
              <Button variant="outline" size="icon">
                <Share2 className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="space-y-8 lg:col-span-2">
            <section>
              <h2 className="mb-4 text-2xl font-semibold text-neutral-900">About this opportunity</h2>
              <p className="leading-relaxed text-neutral-700">{opportunity.description}</p>
            </section>

            <Separator />

            <section>
              <h2 className="mb-4 text-2xl font-semibold text-neutral-900">Responsibilities</h2>
              <ul className="space-y-3">
                {opportunity.responsibilities.map((item, index) => (
                  <li key={index} className="flex items-start gap-3 text-neutral-700">
                    <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </section>

            <Separator />

            <section>
              <h2 className="mb-4 text-2xl font-semibold text-neutral-900">Requirements</h2>
              <ul className="space-y-3">
                {opportunity.requirements.map((item, index) => (
                  <li key={index} className="flex items-start gap-3 text-neutral-700">
                    <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </section>

            <Separator />

            <section>
              <h2 className="mb-4 text-2xl font-semibold text-neutral-900">Benefits</h2>
              <ul className="space-y-3">
                {opportunity.benefits.map((item, index) => (
                  <li key={index} className="flex items-start gap-3 text-neutral-700">
                    <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </section>

            <Separator />

            <section>
              <h2 className="mb-4 text-2xl font-semibold text-neutral-900">
                About {opportunity.organization}
              </h2>
              <p className="leading-relaxed text-neutral-700">{opportunity.about}</p>
            </section>
          </div>

          <div className="lg:col-span-1">
            <div className="sticky top-24 rounded-lg border border-neutral-200 bg-neutral-50 p-6">
              <Button className="mb-4 w-full" size="lg">
                Apply Now
                <ExternalLink className="ml-2 h-4 w-4" />
              </Button>
              <Button variant="outline" className="mb-6 w-full">
                {isSaved ? 'Saved' : 'Save for Later'}
              </Button>

              <Separator className="my-6" />

              <h3 className="mb-4 font-semibold text-neutral-900">Opportunity Details</h3>
              <dl className="space-y-4">
                <div>
                  <dt className="mb-1 text-sm text-neutral-500">Type</dt>
                  <dd className="text-neutral-900">{opportunity.type}</dd>
                </div>
                <div>
                  <dt className="mb-1 text-sm text-neutral-500">Location Type</dt>
                  <dd className="text-neutral-900">{opportunity.locationType}</dd>
                </div>
                <div>
                  <dt className="mb-1 text-sm text-neutral-500">Experience Level</dt>
                  <dd className="text-neutral-900">{opportunity.experience}</dd>
                </div>
                <div>
                  <dt className="mb-1 text-sm text-neutral-500">Application Deadline</dt>
                  <dd className="text-neutral-900">{opportunity.deadline}</dd>
                </div>
              </dl>

              <Separator className="my-6" />

              <h3 className="mb-4 font-semibold text-neutral-900">Skills & Tags</h3>
              <div className="flex flex-wrap gap-2">
                {opportunity.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>

              <Separator className="my-6" />

              <div className="text-sm text-neutral-600">
                <p className="mb-2">Posted: {opportunity.postedDate}</p>
                <p>ID: #{opportunity.id}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OpportunityDetail;
