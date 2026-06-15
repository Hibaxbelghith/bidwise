import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import HomeHero from '../components/home/HomeHero.jsx';
import {
	ArrowRight,
	Briefcase,
	Building2,
	Search,
	Users,
	Zap,
	Sparkles,
	Bot,
	FileText,
	Bell,
	Database,
	CheckCircle2,
	Target,
	BarChart3,
	Rocket,
} from 'lucide-react';

const opportunityTypes = [
	{
		title: 'Jobs',
		description: 'Explore professional roles collected from multiple sources.',
		icon: Briefcase,
		bg: 'bg-blue-100',
		text: 'text-blue-600',
	},
	{
		title: 'Internships',
		description: 'Find internships aligned with your skills and career goals.',
		icon: Users,
		bg: 'bg-green-100',
		text: 'text-green-600',
	},
	{
		title: 'Calls for Tenders',
		description: 'Access structured tender opportunities and key requirements.',
		icon: Zap,
		bg: 'bg-purple-100',
		text: 'text-purple-600',
	},
	{
		title: 'Direct Applications',
		description: 'Apply directly to opportunities published by organizations.',
		icon: FileText,
		bg: 'bg-orange-100',
		text: 'text-orange-600',
	},
	{
		title: 'External Sources',
		description: 'Continue to the original source while keeping your activity organized.',
		icon: Search,
		bg: 'bg-red-100',
		text: 'text-red-600',
	},
];

const Home = () => (
	<main className="overflow-x-hidden">
		<HomeHero />

		{/* Core Features Section */}
		<section className="relative bg-white py-24" aria-labelledby="home-features-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="mb-20 text-center">
					<h2 id="home-features-heading" className="mb-4 text-4xl font-bold text-neutral-900">
						How BidWise Works
					</h2>
					<p className="mx-auto max-w-2xl text-lg text-neutral-600">
						From discovery to application tracking, BidWise brings every step into one clear workflow.
					</p>
				</div>

				<div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Database className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Discover</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Browse jobs, internships and calls for tenders collected from multiple sources
							and published directly by organizations.
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Target className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Match</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Receive personalized recommendations based on your profile, CV, skills and
							preferences, with clear compatibility insights.
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<FileText className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Prepare</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Analyze your CV against an opportunity, improve your professional summary and
							generate a personalized cover letter with AI assistance.
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Bot className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Understand</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Use the contextual AI assistant to understand requirements, ask questions about
							an opportunity and prepare more effectively.
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Bell className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Track</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Save opportunities, manage direct and external applications, follow their status
							and receive relevant notifications from one dashboard.
						</p>
					</div>

					<div className="flex items-center justify-center rounded-2xl border-2 border-dashed border-blue-200 bg-gradient-to-br from-blue-50 to-white p-8">
						<div className="text-center">
							<Rocket className="mx-auto mb-4 h-12 w-12 text-blue-600" />
							<p className="mb-4 text-sm font-medium text-neutral-900">
								Ready to find opportunities that fit your profile?
							</p>
							<Button size="sm" asChild>
								<Link to="/opportunities">
									Explore Opportunities
									<ArrowRight className="ml-2 h-4 w-4" />
								</Link>
							</Button>
						</div>
					</div>
				</div>
			</div>
		</section>

		{/* For Candidates Section */}
		<section className="bg-gradient-to-b from-neutral-50 to-white py-24">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="grid items-center gap-12 lg:grid-cols-2">
					<div>
						<div className="mb-6 inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-700">
							<Users className="h-4 w-4" />
							For Candidates
						</div>

						<h2 className="mb-6 text-4xl font-bold text-neutral-900">
							Turn Your Profile Into Better Opportunities
						</h2>

						<p className="mb-8 text-lg text-neutral-600">
							Build a complete profile, import your CV and let BidWise prioritize opportunities
							that align with your skills, experience and preferences.
						</p>

						<ul className="mb-8 space-y-4">
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>Explainable matching:</strong> See compatibility scores, matched skills and the reasons behind each recommendation.
								</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>Application support:</strong> Compare your CV with each offer and prepare tailored application content.
								</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>Centralized follow-up:</strong> Save opportunities and track direct or external applications in one place.
								</span>
							</li>
						</ul>

						<Button asChild>
							<Link to="/opportunities">
								Explore Recommended Opportunities
								<ArrowRight className="ml-2 h-5 w-5" />
							</Link>
						</Button>
					</div>

					<div className="grid gap-4 sm:grid-cols-2">
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Briefcase className="mb-3 h-8 w-8 text-blue-500" />
							<p className="text-lg font-bold text-neutral-900">Multi-source discovery</p>
							<p className="text-sm text-neutral-600">Fresh opportunities collected from multiple channels.</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<FileText className="mb-3 h-8 w-8 text-green-500" />
							<p className="text-lg font-bold text-neutral-900">CV-powered profile</p>
							<p className="text-sm text-neutral-600">Import your CV to enrich your profile faster.</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Target className="mb-3 h-8 w-8 text-purple-500" />
							<p className="text-lg font-bold text-neutral-900">Explainable AI matching</p>
							<p className="text-sm text-neutral-600">Understand why each opportunity fits your profile.</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Bell className="mb-3 h-8 w-8 text-orange-500" />
							<p className="text-lg font-bold text-neutral-900">Application tracking</p>
							<p className="text-sm text-neutral-600">Keep opportunities and application status organized.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		{/* For Organizations Section */}
		<section className="bg-white py-24">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="grid items-center gap-12 lg:grid-cols-2">
					<div className="order-2 space-y-6 lg:order-1">
						{[
							{
								icon: Zap,
								title: 'Publish in Minutes',
								desc: 'Create and publish jobs, internships and calls for tenders through guided forms.',
							},
							{
								icon: BarChart3,
								title: 'Manage Opportunities',
								desc: 'Edit, activate, suspend or close published opportunities from one workspace.',
							},
							{
								icon: Users,
								title: 'Review Applications',
								desc: 'Review candidates, shortlist or reject applications and keep decisions organized.',
							},
							{
								icon: Building2,
								title: 'Centralized Dashboard',
								desc: 'Monitor opportunity activity, applications and key statistics in one place.',
							},
						].map((item) => {
							const Icon = item.icon;
							return (
								<div key={item.title} className="flex gap-4">
									<div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-blue-100">
										<Icon className="h-5 w-5 text-blue-600" />
									</div>
									<div>
										<h4 className="mb-1 font-semibold text-neutral-900">{item.title}</h4>
										<p className="text-sm text-neutral-600">{item.desc}</p>
									</div>
								</div>
							);
						})}
					</div>

					<div className="order-1 lg:order-2">
						<div className="mb-6 inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-700">
							<Building2 className="h-4 w-4" />
							For Organizations
						</div>

						<h2 className="mb-6 text-4xl font-bold text-neutral-900">
							Publish Opportunities. Manage Candidates.
						</h2>

						<p className="mb-8 text-lg text-neutral-600">
							Give your organization a professional space to publish opportunities, receive
							applications and manage the recruitment process from a centralized dashboard.
						</p>

						<Button asChild className="mb-4">
							<Link to="/organizations">
								Discover the Organization Space
								<ArrowRight className="ml-2 h-5 w-5" />
							</Link>
						</Button>

						<p className="text-sm text-neutral-500">
							Built for structured, transparent opportunity management.
						</p>
					</div>
				</div>
			</div>
		</section>

		{/* Opportunity Types */}
		<section className="bg-gradient-to-b from-neutral-50 to-white py-24" aria-labelledby="home-types-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="mb-16 text-center">
					<h2 id="home-types-heading" className="mb-4 text-4xl font-bold text-neutral-900">
						One Platform, Multiple Application Paths
					</h2>
					<p className="mx-auto max-w-2xl text-lg text-neutral-600">
						Discover opportunities from BidWise organizations and external sources without losing track of your progress.
					</p>
				</div>

				<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
					{opportunityTypes.map((type) => {
						const Icon = type.icon;
						return (
							<div
								key={type.title}
								className="group rounded-xl border border-neutral-200 bg-white p-6 text-center transition-all hover:scale-[1.02] hover:border-blue-200 hover:shadow-lg"
							>
								<div className={`mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl ${type.bg}`}>
									<Icon className={`h-6 w-6 ${type.text}`} />
								</div>
								<h3 className="mb-1 font-semibold text-neutral-900">{type.title}</h3>
								<p className="text-sm leading-6 text-neutral-600">{type.description}</p>
							</div>
						);
					})}
				</div>
			</div>
		</section>

		{/* Final CTA */}
		<section className="relative overflow-hidden bg-gradient-to-br from-blue-700 via-blue-600 to-sky-500 py-24" aria-labelledby="home-cta-heading">
			<div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.18)_1px,transparent_0)] bg-[length:30px_30px] opacity-30" />

			<div className="relative mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
				<div className="mb-8 inline-flex items-center gap-2 rounded-full bg-white/20 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm">
					<Sparkles className="h-4 w-4" />
					For Candidates and Organizations
				</div>

				<h2 id="home-cta-heading" className="mb-6 text-5xl font-bold text-white">
					Make Every Opportunity Count
				</h2>

				<p className="mb-10 text-xl text-blue-100">
					Explore relevant opportunities, prepare stronger applications or publish and manage opportunities for your organization.
				</p>

				<div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
					<Button size="lg" className="min-w-[200px] bg-white text-blue-600 hover:bg-neutral-100" asChild>
						<Link to="/opportunities">
							Explore Opportunities
							<ArrowRight className="ml-2 h-5 w-5" />
						</Link>
					</Button>

					<Button
						size="lg"
						variant="outline"
						className="min-w-[200px] border-white/30 bg-white/10 text-white backdrop-blur-sm hover:bg-white/20"
						asChild
					>
						<Link to="/organizations">For Organizations</Link>
					</Button>
				</div>

				<div className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-4 text-sm text-white/80">
					<div className="flex items-center gap-2">
						<Users className="h-4 w-4" />
						<span>Personalized recommendations</span>
					</div>
					<div className="flex items-center gap-2">
						<Building2 className="h-4 w-4" />
						<span>Direct and external opportunities</span>
					</div>
					<div className="flex items-center gap-2">
						<CheckCircle2 className="h-4 w-4" />
						<span>AI-assisted applications</span>
					</div>
				</div>
			</div>
		</section>
	</main>
);

export default Home;
