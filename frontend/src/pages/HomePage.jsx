import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import HomeHero from '../components/home/HomeHero.jsx';
import { useLanguage } from '../i18n/LanguageContext.jsx';
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

const buildOpportunityTypes = (t) => [
	{
		title: t('home.jobs'),
		description: t('home.jobsDesc'),
		icon: Briefcase,
		bg: 'bg-blue-100',
		text: 'text-blue-600',
	},
	{
		title: t('home.internships'),
		description: t('home.internshipsDesc'),
		icon: Users,
		bg: 'bg-green-100',
		text: 'text-green-600',
	},
	{
		title: t('home.tenders'),
		description: t('home.tendersDesc'),
		icon: Zap,
		bg: 'bg-purple-100',
		text: 'text-purple-600',
	},
	{
		title: t('home.directApplications'),
		description: t('home.directApplicationsDesc'),
		icon: FileText,
		bg: 'bg-orange-100',
		text: 'text-orange-600',
	},
	{
		title: t('home.externalSources'),
		description: t('home.externalSourcesDesc'),
		icon: Search,
		bg: 'bg-red-100',
		text: 'text-red-600',
	},
];

const Home = () => {
	const { t } = useLanguage();
	const opportunityTypes = buildOpportunityTypes(t);
	const organizationFeatures = [
		{ icon: Zap, title: t('home.publishMinutes'), desc: t('home.publishMinutesDesc') },
		{ icon: BarChart3, title: t('home.manageOpportunities'), desc: t('home.manageOpportunitiesDesc') },
		{ icon: Users, title: t('home.reviewApplications'), desc: t('home.reviewApplicationsDesc') },
		{ icon: Building2, title: t('home.centralizedDashboard'), desc: t('home.centralizedDashboardDesc') },
	];

	return (
	<main className="overflow-x-hidden">
		<HomeHero />

		{/* Core Features Section */}
		<section className="relative bg-white py-24" aria-labelledby="home-features-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="mb-20 text-center">
					<h2 id="home-features-heading" className="mb-4 text-4xl font-bold text-neutral-900">
						{t('home.howItWorks')}
					</h2>
					<p className="mx-auto max-w-2xl text-lg text-neutral-600">
						{t('home.howItWorksDesc')}
					</p>
				</div>

				<div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Database className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">{t('home.discover')}</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							{t('home.discoverDesc')}
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Target className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">{t('home.match')}</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							{t('home.matchDesc')}
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<FileText className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">{t('home.prepare')}</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							{t('home.prepareDesc')}
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Bot className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">{t('home.understand')}</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							{t('home.understandDesc')}
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Bell className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">{t('home.track')}</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							{t('home.trackDesc')}
						</p>
					</div>

					<div className="flex items-center justify-center rounded-2xl border-2 border-dashed border-blue-200 bg-gradient-to-br from-blue-50 to-white p-8">
						<div className="text-center">
							<Rocket className="mx-auto mb-4 h-12 w-12 text-blue-600" />
							<p className="mb-4 text-sm font-medium text-neutral-900">
								{t('home.ready')}
							</p>
							<Button size="sm" asChild>
								<Link to="/opportunities">
									{t('common.browseOpportunities')}
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
							{t('home.forCandidates')}
						</div>

						<h2 className="mb-6 text-4xl font-bold text-neutral-900">
							{t('home.candidateTitle')}
						</h2>

						<p className="mb-8 text-lg text-neutral-600">
							{t('home.candidateDesc')}
						</p>

						<ul className="mb-8 space-y-4">
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>{t('home.explainableMatching')}</strong> {t('home.explainableMatchingDesc')}
								</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>{t('home.applicationSupport')}</strong> {t('home.applicationSupportDesc')}
								</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>{t('home.centralizedFollowup')}</strong> {t('home.centralizedFollowupDesc')}
								</span>
							</li>
						</ul>

						<Button asChild>
							<Link to="/opportunities">
								{t('home.exploreRecommended')}
								<ArrowRight className="ml-2 h-5 w-5" />
							</Link>
						</Button>
					</div>

					<div className="grid gap-4 sm:grid-cols-2">
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Briefcase className="mb-3 h-8 w-8 text-blue-500" />
							<p className="text-lg font-bold text-neutral-900">{t('home.multiSourceDiscovery')}</p>
							<p className="text-sm text-neutral-600">{t('home.multiSourceDiscoveryDesc')}</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<FileText className="mb-3 h-8 w-8 text-green-500" />
							<p className="text-lg font-bold text-neutral-900">{t('home.cvPoweredProfile')}</p>
							<p className="text-sm text-neutral-600">{t('home.cvPoweredProfileDesc')}</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Target className="mb-3 h-8 w-8 text-purple-500" />
							<p className="text-lg font-bold text-neutral-900">{t('home.explainableAiMatching')}</p>
							<p className="text-sm text-neutral-600">{t('home.explainableAiMatchingDesc')}</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Bell className="mb-3 h-8 w-8 text-orange-500" />
							<p className="text-lg font-bold text-neutral-900">{t('home.applicationTracking')}</p>
							<p className="text-sm text-neutral-600">{t('home.applicationTrackingDesc')}</p>
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
						{organizationFeatures.map((item) => {
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
							{t('common.forOrganizations')}
						</div>

						<h2 className="mb-6 text-4xl font-bold text-neutral-900">
							{t('home.organizationTitle')}
						</h2>

						<p className="mb-8 text-lg text-neutral-600">
							{t('home.organizationDesc')}
						</p>

						<Button asChild className="mb-4">
							<Link to="/organizations">
								{t('home.discoverOrgSpace')}
								<ArrowRight className="ml-2 h-5 w-5" />
							</Link>
						</Button>

						<p className="text-sm text-neutral-500">
							{t('home.orgBuiltFor')}
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
						{t('home.pathsTitle')}
					</h2>
					<p className="mx-auto max-w-2xl text-lg text-neutral-600">
						{t('home.pathsDesc')}
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
					{t('home.forBoth')}
				</div>

				<h2 id="home-cta-heading" className="mb-6 text-5xl font-bold text-white">
					{t('home.ctaTitle')}
				</h2>

				<p className="mb-10 text-xl text-blue-100">
					{t('home.ctaDesc')}
				</p>

				<div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
					<Button
  size="lg"
  className="min-w-[200px] bg-blue-600 text-white hover:bg-blue-700"
  asChild
>
  <Link to="/opportunities">
    {t('common.browseOpportunities')}
    <ArrowRight className="ml-2 h-5 w-5" />
  </Link>
</Button>

					<Button
						size="lg"
						variant="outline"
						className="min-w-[200px] border-white/30 bg-white/10 text-white backdrop-blur-sm hover:bg-white/20"
						asChild
					>
						<Link to="/organizations">{t('common.forOrganizations')}</Link>
					</Button>
				</div>

				<div className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-4 text-sm text-white/80">
					<div className="flex items-center gap-2">
						<Users className="h-4 w-4" />
						<span>{t('home.personalizedRecommendations')}</span>
					</div>
					<div className="flex items-center gap-2">
						<Building2 className="h-4 w-4" />
						<span>{t('home.directExternal')}</span>
					</div>
					<div className="flex items-center gap-2">
						<CheckCircle2 className="h-4 w-4" />
						<span>{t('home.aiAssisted')}</span>
					</div>
				</div>
			</div>
		</section>
	</main>
	);
};

export default Home;
