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
} from 'lucide-react';

const Home = () => (
	<main className="overflow-x-hidden">
		{/* Hero Section - Modern gradient with subtle animation */}
		<section className="relative min-h-[85vh] bg-gradient-to-br from-neutral-50 via-blue-50/30 to-white">
			{/* Subtle background pattern */}
			<div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=%2260%22 height=%2260%22 viewBox=%220 0 60 60%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cg fill=%22none%22 fill-rule=%22evenodd%22%3E%3Cg fill=%22%239ca3af%22 fill-opacity=%220.03%22%3E%3Cpath d=%22M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z%22/%3E%3C/g%3E%3C/g%3E%3C/svg%3E')] opacity-40"></div>
			
			<div className="relative mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8 lg:py-32">
				<div className="mx-auto max-w-4xl text-center">
					<h1 className="mb-6 text-5xl font-bold tracking-tight text-neutral-900 sm:text-6xl lg:text-7xl">
						Your Next Opportunity
						<span className="block bg-gradient-to-r from-blue-600 to-blue-500 bg-clip-text text-transparent">
							Starts Here
						</span>
					</h1>
					
					<p className="mx-auto mb-10 max-w-2xl text-lg text-neutral-600 sm:text-xl">
						BidWise aggregates jobs, internships, projects, tenders, and funding from across Tunisia.
						AI-powered matching, smart applications, and real-time tracking—all in one platform.
					</p>
					
					<div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
						<Button size="lg" className="group min-w-[200px]" asChild>
							<Link to="/opportunities">
								Explore Opportunities
								<ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" aria-hidden="true" />
							</Link>
						</Button>
						<Button size="lg" variant="outline" className="min-w-[200px] border-neutral-300 bg-white/50 backdrop-blur-sm hover:bg-white" asChild>
							<Link to="/organizations">For Organizations</Link>
						</Button>
					</div>
					
					{/* Trust indicators */}
					<div className="mt-16 flex flex-wrap items-center justify-center gap-8 text-sm text-neutral-500">
						<div className="flex items-center gap-2">
							<CheckCircle2 className="h-5 w-5 text-green-500" />
							<span>Updated Daily</span>
						</div>
						<div className="flex items-center gap-2">
							<Shield className="h-5 w-5 text-blue-500" />
							<span>Verified Sources</span>
						</div>
						<div className="flex items-center gap-2">
							<Globe className="h-5 w-5 text-purple-500" />
							<span>All Tunisia Coverage</span>
						</div>
					</div>
				</div>
			</div>
		</section>

				{/* Core Features Section - 5 pillars */}
		<section className="relative bg-white py-24" aria-labelledby="home-features-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="mb-20 text-center">
					<h2 id="home-features-heading" className="mb-4 text-4xl font-bold text-neutral-900">
						How BidWise Works
					</h2>
					<p className="mx-auto max-w-2xl text-lg text-neutral-600">
						Five powerful features that transform how you find and apply to opportunities
					</p>
				</div>

				{/* Feature Cards Grid */}
				<div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
					{/* Collect */}
					<div className="group relative overflow-hidden rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:shadow-xl hover:scale-[1.02]">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
							<Database className="h-6 w-6 text-blue-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Collect</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Automated multi-source scraping from Keejob, EmploiTunisie and official portals. 
							Updated daily—no manual browsing. Jobs, internships, projects, and funding in one feed.
						</p>
					</div>

					{/* Recommend */}
					<div className="group relative overflow-hidden rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:shadow-xl hover:scale-[1.02]">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-purple-100">
							<Target className="h-6 w-6 text-purple-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Recommend</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Every opportunity gets a real compatibility score based on your actual profile, 
							skills and history. AI-powered matching that understands your career goals.
						</p>
					</div>

					{/* Apply */}
					<div className="group relative overflow-hidden rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:shadow-xl hover:scale-[1.02]">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-green-100">
							<FileText className="h-6 w-6 text-green-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Apply</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							AI-generated cover letters contextualised to each specific opportunity. 
							Tailored applications that highlight your relevant experience.
						</p>
					</div>

					{/* Assist */}
					<div className="group relative overflow-hidden rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:shadow-xl hover:scale-[1.02]">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-orange-100">
							<Bot className="h-6 w-6 text-orange-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Assist</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Integrated AI chatbot guides you through search, answers questions about opportunities, 
							and helps at every step—all within the platform.
						</p>
					</div>

					{/* Track */}
					<div className="group relative overflow-hidden rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 p-8 transition-all hover:shadow-xl hover:scale-[1.02]">
						<div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-red-100">
							<Bell className="h-6 w-6 text-red-600" />
						</div>
						<h3 className="mb-3 text-xl font-semibold text-neutral-900">Track</h3>
						<p className="text-sm leading-relaxed text-neutral-600">
							Full application history, saved opportunities, smart notifications for new matches, 
							and profile visibility controls for recruiters.
						</p>
					</div>

					{/* CTA Card */}
					<div className="flex items-center justify-center rounded-2xl border-2 border-dashed border-neutral-300 bg-gradient-to-br from-blue-50 to-white p-8">
						<div className="text-center">
							<Sparkles className="mx-auto mb-4 h-12 w-12 text-blue-500" />
							<p className="mb-4 text-sm font-medium text-neutral-900">
								Ready to transform your job search?
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
									<strong>Smart Matching:</strong> AI analyzes your CV and suggests opportunities with real compatibility scores
								</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>One-Click Applications:</strong> Generate tailored cover letters instantly
								</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="mt-1 h-5 w-5 flex-shrink-0 text-green-500" />
								<span className="text-neutral-700">
									<strong>Real-Time Alerts:</strong> Get notified when new matching opportunities appear
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
					<div className="relative">
						{/* Stats Cards */}
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
			</div>
		</section>

		{/* For Organizations Section */}
		<section className="bg-white py-24">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="grid items-center gap-12 lg:grid-cols-2">
					<div className="order-2 lg:order-1">
						{/* Feature List */}
						<div className="space-y-6">
							<div className="flex gap-4">
								<div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-blue-100">
									<Zap className="h-5 w-5 text-blue-600" />
								</div>
								<div>
									<h4 className="mb-1 font-semibold text-neutral-900">Publish in Minutes</h4>
									<p className="text-sm text-neutral-600">
										Streamlined posting process for jobs, projects, and funding calls
									</p>
								</div>
							</div>
							<div className="flex gap-4">
								<div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-purple-100">
									<BarChart3 className="h-5 w-5 text-purple-600" />
								</div>
								<div>
									<h4 className="mb-1 font-semibold text-neutral-900">Track Performance</h4>
									<p className="text-sm text-neutral-600">
										Detailed analytics on views, applications, and candidate quality
									</p>
								</div>
							</div>
							<div className="flex gap-4">
								<div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-green-100">
									<Users className="h-5 w-5 text-green-600" />
								</div>
								<div>
									<h4 className="mb-1 font-semibold text-neutral-900">Reach Top Talent</h4>
									<p className="text-sm text-neutral-600">
										Connect with pre-qualified candidates actively looking in Tunisia
									</p>
								</div>
							</div>
							<div className="flex gap-4">
								<div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-orange-100">
									<Building2 className="h-5 w-5 text-orange-600" />
								</div>
								<div>
									<h4 className="mb-1 font-semibold text-neutral-900">Centralized Dashboard</h4>
									<p className="text-sm text-neutral-600">
										Manage all applications and communications in one organized space
									</p>
								</div>
							</div>
						</div>
					</div>
					<div className="order-1 lg:order-2">
						<div className="mb-6 inline-flex items-center gap-2 rounded-full bg-purple-100 px-3 py-1 text-sm font-medium text-purple-700">
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

		{/* Opportunity Types Grid */}
		<section className="bg-gradient-to-b from-neutral-50 to-white py-24" aria-labelledby="home-types-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="mb-16 text-center">
					<h2 id="home-types-heading" className="mb-4 text-4xl font-bold text-neutral-900">
						Every Type of Opportunity
					</h2>
					<p className="mx-auto max-w-2xl text-lg text-neutral-600">
						From entry-level positions to executive roles, research grants to startup funding—find it all here
					</p>
				</div>

				<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
					{[
						{ title: 'Jobs', count: '1,234', icon: Briefcase, color: 'blue' },
						{ title: 'Internships', count: '456', icon: Users, color: 'green' },
						{ title: 'Projects', count: '567', icon: Zap, color: 'purple' },
						{ title: 'Funding', count: '189', icon: TrendingUp, color: 'orange' },
						{ title: 'Research', count: '342', icon: Search, color: 'red' },
					].map((type) => (
						<div
							key={type.title}
							className="group relative overflow-hidden rounded-xl border border-neutral-200 bg-white p-6 text-center transition-all hover:shadow-lg hover:scale-[1.02] hover:border-neutral-300"
						>
							<div className={`mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-${type.color}-100`}>
								<type.icon className={`h-6 w-6 text-${type.color}-600`} aria-hidden="true" />
							</div>
							<h3 className="mb-1 font-semibold text-neutral-900">{type.title}</h3>
							<p className="text-2xl font-bold text-neutral-900">{type.count}</p>
							<p className="text-xs text-neutral-500">Active now</p>
						</div>
					))}
				</div>
			</div>
		</section>

				{/* Final CTA Section */}
		<section className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-500 to-purple-600 py-24" aria-labelledby="home-cta-heading">
			{/* Background decoration */}
			<div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=%2260%22 height=%2260%22 viewBox=%220 0 60 60%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cg fill=%22none%22 fill-rule=%22evenodd%22%3E%3Cg fill=%22%23ffffff%22 fill-opacity=%220.08%22%3E%3Cpath d=%22M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z%22/%3E%3C/g%3E%3C/g%3E%3C/svg%3E')]"></div>
			
			<div className="relative mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
				<div className="mb-8 inline-flex items-center gap-2 rounded-full bg-white/20 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm">
					<Sparkles className="h-4 w-4" />
					Start Free Today
				</div>
				<h2 id="home-cta-heading" className="mb-6 text-5xl font-bold text-white">
					Your Future Awaits
				</h2>
				<p className="mb-10 text-xl text-blue-100">
					Join thousands of professionals and organizations already using BidWise 
					to connect with opportunities in Tunisia
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
				
				{/* Social proof */}
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
