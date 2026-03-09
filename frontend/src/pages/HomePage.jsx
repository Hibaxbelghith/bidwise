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
} from 'lucide-react';

const Home = () => (
	<main>
		<section className="relative bg-gradient-to-b from-blue-50 to-white">
			<div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
				<div className="mx-auto max-w-3xl text-center">
					<h1 className="mb-6 text-5xl font-bold text-neutral-900">
						Discover Professional Opportunities with BidWise
					</h1>
					<p className="mb-10 text-xl text-neutral-600">
						An API-first platform that helps you find and track job offers, projects,
						funding, and research opportunities in one place.
					</p>
					<div className="flex flex-col justify-center gap-4 sm:flex-row">
						<Button size="lg" asChild>
							<Link to="/opportunities">
								Browse Opportunities <ArrowRight className="ml-2 h-5 w-5" aria-hidden="true" />
							</Link>
						</Button>
						<Button size="lg" variant="outline" asChild>
							<Link to="/organization/post">Post Opportunity</Link>
						</Button>
					</div>
				</div>
			</div>
		</section>

		<section className="bg-white py-20" aria-labelledby="home-features-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="mb-16 text-center">
					<h2 id="home-features-heading" className="mb-4 text-3xl font-bold text-neutral-900">
						Built for Candidates and Organizations
					</h2>
					<p className="text-lg text-neutral-600">
						Simple, powerful tools to connect talent with opportunities
					</p>
				</div>

				<div className="mb-20 grid gap-12 md:grid-cols-2">
					<div className="rounded-xl border border-neutral-200 bg-neutral-50 p-8">
						<div className="mb-6 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100">
							<Users className="h-6 w-6 text-blue-600" aria-hidden="true" />
						</div>
						<h3 className="mb-4 text-2xl font-semibold text-neutral-900">For Candidates</h3>
						<p className="mb-6 text-neutral-600">
							Search, filter, and track professional opportunities tailored to your needs.
							Never miss the perfect opportunity.
						</p>
						<ul className="mb-8 space-y-3">
							<li className="flex items-start gap-3">
								<Search className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" aria-hidden="true" />
								<span className="text-neutral-700">Advanced search and filtering</span>
							</li>
							<li className="flex items-start gap-3">
								<Briefcase className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" aria-hidden="true" />
								<span className="text-neutral-700">Track and follow opportunities</span>
							</li>
							<li className="flex items-start gap-3">
								<TrendingUp className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" aria-hidden="true" />
								<span className="text-neutral-700">Get notifications on updates</span>
							</li>
						</ul>
						<Button asChild className="w-full">
							<Link to="/opportunities">Start Searching</Link>
						</Button>
					</div>

					<div className="rounded-xl border border-neutral-200 bg-neutral-50 p-8">
						<div className="mb-6 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100">
							<Building2 className="h-6 w-6 text-blue-600" aria-hidden="true" />
						</div>
						<h3 className="mb-4 text-2xl font-semibold text-neutral-900">For Organizations</h3>
						<p className="mb-6 text-neutral-600">
							Publish opportunities and reach qualified candidates. Manage all your
							listings in one place with our powerful API.
						</p>
						<ul className="mb-8 space-y-3">
							<li className="flex items-start gap-3">
								<Zap className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" aria-hidden="true" />
								<span className="text-neutral-700">Quick and easy posting</span>
							</li>
							<li className="flex items-start gap-3">
								<Building2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" aria-hidden="true" />
								<span className="text-neutral-700">Manage multiple opportunities</span>
							</li>
							<li className="flex items-start gap-3">
								<TrendingUp className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600" aria-hidden="true" />
								<span className="text-neutral-700">API-first integration</span>
							</li>
						</ul>
						<Button asChild className="w-full">
							<Link to="/organization/post">Post Opportunity</Link>
						</Button>
					</div>
				</div>
			</div>
		</section>

		<section className="bg-neutral-50 py-20" aria-labelledby="home-types-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="mb-16 text-center">
					<h2 id="home-types-heading" className="mb-4 text-3xl font-bold text-neutral-900">
						All Types of Opportunities
					</h2>
					<p className="text-lg text-neutral-600">
						From job offers to research grants, find everything in one place
					</p>
				</div>

				<div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
					{[
						{ title: 'Job Offers', count: '1,234', icon: Briefcase },
						{ title: 'Projects', count: '567', icon: Zap },
						{ title: 'Funding', count: '189', icon: TrendingUp },
						{ title: 'Research', count: '342', icon: Search },
					].map((type) => (
						<div
							key={type.title}
							className="rounded-lg border border-neutral-200 bg-white p-6 text-center transition-colors hover:border-blue-300"
						>
							<div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100">
							<type.icon className="h-6 w-6 text-blue-600" aria-hidden="true" />
							</div>
							<h3 className="mb-2 font-semibold text-neutral-900">{type.title}</h3>
							<p className="text-2xl font-bold text-blue-600">{type.count}</p>
							<p className="text-sm text-neutral-500">Active opportunities</p>
						</div>
					))}
				</div>
			</div>
		</section>

		<section className="bg-blue-600 py-20" aria-labelledby="home-cta-heading">
			<div className="mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
				<h2 id="home-cta-heading" className="mb-4 text-3xl font-bold text-white">Ready to Get Started?</h2>
				<p className="mb-8 text-xl text-blue-100">
					Join thousands of candidates and organizations using BidWise
				</p>
				<div className="flex flex-col justify-center gap-4 sm:flex-row">
					<Button size="lg" variant="secondary" asChild>
						<Link to="/opportunities">Browse Opportunities</Link>
					</Button>
					<Button
						size="lg"
						variant="outline"
						className="border-white bg-transparent text-white hover:bg-blue-700"
						asChild
					>
						<Link to="/organization/dashboard">For Organizations</Link>
					</Button>
				</div>
			</div>
		</section>
	</main>
);

export default Home;
