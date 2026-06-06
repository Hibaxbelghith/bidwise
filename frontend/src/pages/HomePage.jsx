import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button.jsx';
import {
	ArrowRight,
	Briefcase,
	Building2,
	Search,
	TrendingUp,
	Users,
	Zap,
	Sparkles,
	Bot,
	FileText,
	Bell,
	Database,
	CheckCircle2,
	Clock,
	Target,
	Globe,
	Shield,
	BarChart3,
	Layers,
	Rocket,
} from 'lucide-react';

const opportunityTypes = [
	{
		title: 'Jobs',
		count: '1,234',
		icon: Briefcase,
		bg: 'bg-blue-100',
		text: 'text-blue-600',
	},
	{
		title: 'Internships',
		count: '456',
		icon: Users,
		bg: 'bg-green-100',
		text: 'text-green-600',
	},
	{
		title: 'Projects',
		count: '567',
		icon: Zap,
		bg: 'bg-purple-100',
		text: 'text-purple-600',
	},
	{
		title: 'Funding',
		count: '189',
		icon: TrendingUp,
		bg: 'bg-orange-100',
		text: 'text-orange-600',
	},
	{
		title: 'Research',
		count: '342',
		icon: Search,
		bg: 'bg-red-100',
		text: 'text-red-600',
	},
];

const heroFeatures = [
	{ icon: Search, label: 'AI Matching' },
	{ icon: FileText, label: 'Smart Applications' },
	{ icon: BarChart3, label: 'Real-time Tracking' },
	{ icon: Bell, label: 'Instant Alerts' },
	{ icon: Shield, label: 'Trusted & Secure' },
];

const Home = () => (
	<main className="overflow-x-hidden">
	<section className="relative min-h-[82vh] overflow-hidden bg-gradient-to-b from-[#f8fbff] via-white to-[#dff1ff]">
			{/* Soft blue corner glow */}
			<div className="absolute left-0 top-0 h-[320px] w-[320px] rounded-full bg-blue-200/50 blur-3xl" />
			<div className="absolute right-0 bottom-0 h-[420px] w-[420px] rounded-full bg-blue-200/40 blur-3xl" />

			{/* Wave background */}
			<div className="absolute inset-x-0 bottom-0 h-[45%] overflow-hidden">
				<div className="absolute bottom-[-35%] left-[-10%] h-full w-[120%] rounded-[50%_50%_0_0] bg-blue-200/45" />
				<div className="absolute bottom-[-42%] left-[-8%] h-full w-[120%] rounded-[45%_55%_0_0] bg-blue-100/70" />
			</div>

			<div className="relative z-10 mx-auto flex min-h-[82vh] max-w-6xl flex-col items-center justify-center px-4 text-center">
				<p className="mb-6 text-sm font-extrabold uppercase tracking-[0.2em] text-blue-600">
					Trusted by over 1.2 million job seekers!
				</p>

				<h1 className="max-w-4xl text-5xl font-black leading-[1.05] tracking-tight text-slate-950 sm:text-6xl lg:text-7xl">
					Land your{' '}
					<span className="text-blue-600">
						dream job.
					</span>
					<br />
					Without the stress.
				</h1>

				<div className="mt-10 flex flex-wrap items-center justify-center gap-x-8 gap-y-4 text-lg text-slate-800">
					{[
						'AI Resume Builder',
						'Automated Job Tracking',
						'Optimize your LinkedIn Profile',
						'And Much More...',
					].map((item) => (
						<div key={item} className="flex items-center gap-3">
							<span className="flex h-7 w-7 items-center justify-center rounded-full border border-blue-500 text-blue-600">
								<CheckCircle2 className="h-4 w-4" />
							</span>
							<span>{item}</span>
						</div>
					))}
				</div>

				<button className="mt-14 rounded-xl bg-blue-600 px-14 py-5 text-sm font-extrabold uppercase tracking-[0.18em] text-white shadow-xl shadow-blue-600/25 transition hover:-translate-y-0.5 hover:bg-blue-700">
					Sign up for free
				</button>

				<div className="mt-28 flex flex-col items-center">
					<div className="flex -space-x-3">
						{[
							'https://i.pravatar.cc/80?img=12',
							'https://i.pravatar.cc/80?img=47',
							'https://i.pravatar.cc/80?img=15',
							'https://i.pravatar.cc/80?img=33',
							'https://i.pravatar.cc/80?img=49',
						].map((src, index) => (
							<img
								key={index}
								src={src}
								alt=""
								className="h-12 w-12 rounded-full border-4 border-white object-cover shadow-sm"
							/>
						))}
						<span className="relative flex h-3 w-3 rounded-full bg-green-400 ring-4 ring-white" />
					</div>

					<p className="mt-6 max-w-lg text-base italic leading-7 text-slate-800">
						"I got recruiters from Amazon, Wise, and other companies
						<br className="hidden sm:block" />
						reaching out to me already!"
					</p>
				</div>
			</div>
		</section>

		{/* Core Features Section */}
		<section className="relative bg-white py-24" aria-labelledby="home-features-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="mb-20 text-center">
					<h2 id="home-features-heading" className="mb-4 text-4xl font-bold text-neutral-900">
						How BidWise Works
					</h2>
					<p className="mx-auto max-w-2xl text-lg text-neutral-600">
						Five powerful features that transform how you find and apply to opportunities.
					</p>
				</div>

				<div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Database className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Collect</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Automated multi-source scraping from job portals, project platforms and official sources.
							Jobs, projects, tenders and funding in one intelligent feed.
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Target className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Recommend</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							AI analyzes your profile, skills and preferences to recommend the most relevant
							opportunities with a clear compatibility score.
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<FileText className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Apply</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Generate and optimize tailored applications using NLP and generative AI according
							to each opportunity’s requirements.
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Bot className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Assist</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							An integrated chatbot helps users search, understand opportunities and prepare better
							applications directly inside the platform.
						</p>
					</div>

					<div className="group rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:scale-[1.02] hover:shadow-xl">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Bell className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Track</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Save opportunities, track applications, receive alerts and manage your progress
							from one simple dashboard.
						</p>
					</div>

					<div className="flex items-center justify-center rounded-2xl border-2 border-dashed border-blue-200 bg-gradient-to-br from-blue-50 to-white p-8">
						<div className="text-center">
							<Rocket className="mx-auto mb-4 h-12 w-12 text-blue-600" />
							<p className="mb-4 text-sm font-medium text-neutral-900">
								Ready to transform your opportunity search?
							</p>
							<Button size="sm" asChild>
								<Link to="/opportunities">
									Get Started Free
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
							Stop Missing Perfect Opportunities
						</h2>

						<p className="mb-8 text-lg text-neutral-600">
							Our AI understands your profile and automatically surfaces the best matches.
							No more endless scrolling through irrelevant postings.
						</p>

						<ul className="mb-8 space-y-4">
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>Smart Matching:</strong> AI analyzes your CV and suggests opportunities with compatibility scores.
								</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>AI Applications:</strong> Generate tailored applications instantly.
								</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>Real-Time Alerts:</strong> Get notified when matching opportunities appear.
								</span>
							</li>
						</ul>

						<Button asChild>
							<Link to="/opportunities">
								Find Your Next Opportunity
								<ArrowRight className="ml-2 h-5 w-5" />
							</Link>
						</Button>
					</div>

					<div className="grid gap-4 sm:grid-cols-2">
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Briefcase className="mb-3 h-8 w-8 text-blue-500" />
							<p className="text-3xl font-bold text-neutral-900">2,450+</p>
							<p className="text-sm text-neutral-600">Active Opportunities</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Clock className="mb-3 h-8 w-8 text-green-500" />
							<p className="text-3xl font-bold text-neutral-900">24h</p>
							<p className="text-sm text-neutral-600">Update Frequency</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Target className="mb-3 h-8 w-8 text-purple-500" />
							<p className="text-3xl font-bold text-neutral-900">95%</p>
							<p className="text-sm text-neutral-600">Match Accuracy</p>
						</div>
						<div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
							<Layers className="mb-3 h-8 w-8 text-orange-500" />
							<p className="text-3xl font-bold text-neutral-900">15+</p>
							<p className="text-sm text-neutral-600">Data Sources</p>
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
								desc: 'Streamlined posting process for jobs, projects and funding calls.',
							},
							{
								icon: BarChart3,
								title: 'Track Performance',
								desc: 'Analytics on views, applications and candidate quality.',
							},
							{
								icon: Users,
								title: 'Reach Top Talent',
								desc: 'Connect with qualified candidates actively looking for opportunities.',
							},
							{
								icon: Building2,
								title: 'Centralized Dashboard',
								desc: 'Manage applications and communications in one organized space.',
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
							Find the Right Talent, Faster
						</h2>

						<p className="mb-8 text-lg text-neutral-600">
							Reach qualified candidates with our AI-powered platform.
							Publish once, manage everything from a single dashboard.
						</p>

						<Button asChild className="mb-4">
							<Link to="/organizations">
								Post Your First Opportunity
								<ArrowRight className="ml-2 h-5 w-5" />
							</Link>
						</Button>

						<p className="text-sm text-neutral-500">
							Free to post • No credit card required
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
						Every Type of Opportunity
					</h2>
					<p className="mx-auto max-w-2xl text-lg text-neutral-600">
						From jobs and internships to research grants, tenders and startup funding.
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
								<p className="text-2xl font-bold text-neutral-900">{type.count}</p>
								<p className="text-xs text-neutral-500">Active now</p>
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
					Start Free Today
				</div>

				<h2 id="home-cta-heading" className="mb-6 text-5xl font-bold text-white">
					Your Future Awaits
				</h2>

				<p className="mb-10 text-xl text-blue-100">
					Join professionals and organizations already using BidWise to connect with better opportunities.
				</p>

				<div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
					<Button size="lg" className="min-w-[200px] bg-white text-blue-600 hover:bg-neutral-100" asChild>
						<Link to="/opportunities">
							Start Exploring
							<ArrowRight className="ml-2 h-5 w-5" />
						</Link>
					</Button>

					<Button
						size="lg"
						variant="outline"
						className="min-w-[200px] border-white/30 bg-white/10 text-white backdrop-blur-sm hover:bg-white/20"
						asChild
					>
						<Link to="/organizations">Post Opportunities</Link>
					</Button>
				</div>

				<div className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-4 text-sm text-white/80">
					<div className="flex items-center gap-2">
						<Users className="h-4 w-4" />
						<span>5,000+ Active Users</span>
					</div>
					<div className="flex items-center gap-2">
						<Building2 className="h-4 w-4" />
						<span>200+ Organizations</span>
					</div>
					<div className="flex items-center gap-2">
						<CheckCircle2 className="h-4 w-4" />
						<span>10,000+ Matches Made</span>
					</div>
				</div>
			</div>
		</section>
	</main>
);

export default Home;