import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import PipelineMetrics from '../../components/PipelineMetrics.jsx';
import { Briefcase, Clock, Bookmark, Building2, MapPin, DollarSign, Calendar, TrendingUp } from 'lucide-react';

const Dashboard = () => {
	const { user } = useAuth();

	// Mock data - replace with backend fetch
	const savedOpportunities = [
		{
			id: '2',
			title: 'AI Research Grant',
			organization: 'National Science Foundation',
			type: 'Funding',
			location: 'Nationwide',
			salary: '$500k - $2M',
			deadline: 'Apr 30, 2026',
			status: 'Active',
			tags: ['AI/ML', 'Research', 'Healthcare'],
		},
		{
			id: '5',
			title: 'UX Designer',
			organization: 'DesignHub',
			type: 'Job Offer',
			location: 'New York, NY',
			salary: '$90k - $120k',
			deadline: 'Mar 20, 2026',
			status: 'Active',
			tags: ['UI/UX', 'Figma', 'Design Systems'],
		},
		{
			id: '8',
			title: 'Open Source Development',
			organization: 'Mozilla Foundation',
			type: 'Project',
			location: 'Remote',
			salary: '$60k - $80k',
			deadline: 'Mar 28, 2026',
			status: 'Active',
			tags: ['JavaScript', 'Open Source'],
		},
	];

	const appliedOpportunities = [
		{
			id: '1',
			title: 'Senior Software Engineer',
			organization: 'TechCorp Inc.',
			type: 'Job Offer',
			appliedDate: 'Feb 5, 2026',
			status: 'Under Review',
			lastUpdate: '2 days ago',
		},
		{
			id: '7',
			title: 'Data Science Research',
			organization: 'Stanford University',
			type: 'Research',
			appliedDate: 'Jan 28, 2026',
			status: 'Interview Scheduled',
			lastUpdate: '5 days ago',
		},
	];

	return (
		<section className="bg-neutral-50" aria-labelledby="dashboard-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
				{/* Header */}
				<div className="mb-8">
					<h1 id="dashboard-heading" className="text-3xl font-bold text-neutral-900 mb-2">My Dashboard</h1>
					<p className="text-neutral-600">Track and manage your opportunities</p>
				</div>

				{/* Stats Cards */}
				<div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8" role="region" aria-label="Dashboard statistics">
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-sm font-medium text-neutral-600">Saved</CardTitle>
						</CardHeader>
						<CardContent>
							<div className="flex items-center justify-between">
								<p className="text-3xl font-bold text-neutral-900">{savedOpportunities.length}</p>
								<Bookmark className="w-8 h-8 text-blue-600" aria-hidden="true" />
							</div>
						</CardContent>
					</Card>

					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-sm font-medium text-neutral-600">Applied</CardTitle>
						</CardHeader>
						<CardContent>
							<div className="flex items-center justify-between">
								<p className="text-3xl font-bold text-neutral-900">{appliedOpportunities.length}</p>
								<Briefcase className="w-8 h-8 text-blue-600" aria-hidden="true" />
							</div>
						</CardContent>
					</Card>

					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-sm font-medium text-neutral-600">Interviews</CardTitle>
						</CardHeader>
						<CardContent>
							<div className="flex items-center justify-between">
								<p className="text-3xl font-bold text-neutral-900">1</p>
								<Calendar className="w-8 h-8 text-blue-600" aria-hidden="true" />
							</div>
						</CardContent>
					</Card>

					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-sm font-medium text-neutral-600">Profile Views</CardTitle>
						</CardHeader>
						<CardContent>
							<div className="flex items-center justify-between">
								<p className="text-3xl font-bold text-neutral-900">24</p>
								<TrendingUp className="w-8 h-8 text-blue-600" aria-hidden="true" />
							</div>
						</CardContent>
					</Card>
				</div>

				{/* Main Content 
				<PipelineMetrics />
				*/}

				<Tabs defaultValue="saved" className="space-y-6">
					<TabsList aria-label="Opportunity categories">
						<TabsTrigger value="saved">Saved Opportunities</TabsTrigger>
						<TabsTrigger value="applied">Applications</TabsTrigger>
						<TabsTrigger value="recommended">Recommended</TabsTrigger>
					</TabsList>

					{/* Saved Opportunities */}
					<TabsContent value="saved" className="space-y-4">
						{savedOpportunities.length === 0 ? (
							<Card>
								<CardContent className="py-12 text-center">
									<Bookmark className="w-12 h-12 text-neutral-300 mx-auto mb-4" aria-hidden="true" />
									<p className="text-neutral-600 mb-4">No saved opportunities yet</p>
									<Button asChild>
										<Link to="/opportunities">Browse Opportunities</Link>
									</Button>
								</CardContent>
							</Card>
						) : (
							savedOpportunities.map((opportunity) => (
								<Card key={opportunity.id} className="hover:border-blue-300 transition-colors">
									<CardContent className="p-6">
										<div className="flex items-start justify-between gap-4">
											<div className="flex-1">
												<div className="flex items-center gap-3 mb-2">
													<Link
														to={`/opportunities/${opportunity.id}`}
														className="text-xl font-semibold text-neutral-900 hover:text-blue-600"
													>
														{opportunity.title}
													</Link>
													<Badge>{opportunity.type}</Badge>
													<Badge variant="outline" className="text-green-600 border-green-600">
														{opportunity.status}
													</Badge>
												</div>
												<div className="flex items-center gap-4 text-sm text-neutral-600 mb-3">
													<span className="flex items-center gap-1">
														<Building2 className="w-4 h-4" />
														{opportunity.organization}
													</span>
													<span className="flex items-center gap-1">
														<MapPin className="w-4 h-4" />
														{opportunity.location}
													</span>
													<span className="flex items-center gap-1">
														<DollarSign className="w-4 h-4" />
														{opportunity.salary}
													</span>
												</div>
												<div className="flex flex-wrap gap-2 mb-3">
													{opportunity.tags.map((tag) => (
														<Badge key={tag} variant="secondary">
															{tag}
														</Badge>
													))}
												</div>
												<p className="text-sm text-neutral-500">
													Deadline: {opportunity.deadline}
												</p>
											</div>
											<div className="flex gap-2">
												<Button asChild>
													<Link to={`/opportunities/${opportunity.id}`}>View</Link>
												</Button>
												<Button variant="outline">Remove</Button>
											</div>
										</div>
									</CardContent>
								</Card>
							))
						)}
					</TabsContent>

					{/* Applied Opportunities */}
					<TabsContent value="applied" className="space-y-4">
						{appliedOpportunities.length === 0 ? (
							<Card>
								<CardContent className="py-12 text-center">
									<Briefcase className="w-12 h-12 text-neutral-300 mx-auto mb-4" aria-hidden="true" />
									<p className="text-neutral-600 mb-4">No applications yet</p>
									<Button asChild>
										<Link to="/opportunities">Start Applying</Link>
									</Button>
								</CardContent>
							</Card>
						) : (
							appliedOpportunities.map((opportunity) => (
								<Card key={opportunity.id} className="hover:border-blue-300 transition-colors">
									<CardContent className="p-6">
										<div className="flex items-start justify-between gap-4">
											<div className="flex-1">
												<div className="flex items-center gap-3 mb-2">
													<Link
														to={`/opportunities/${opportunity.id}`}
														className="text-xl font-semibold text-neutral-900 hover:text-blue-600"
													>
														{opportunity.title}
													</Link>
													<Badge>{opportunity.type}</Badge>
													<Badge
														variant="outline"
														className={
															opportunity.status === 'Interview Scheduled'
																? 'text-green-600 border-green-600'
																: 'text-blue-600 border-blue-600'
														}
													>
														{opportunity.status}
													</Badge>
												</div>
												<p className="text-neutral-600 mb-3">{opportunity.organization}</p>
												<div className="flex items-center gap-4 text-sm text-neutral-500">
													<span>Applied: {opportunity.appliedDate}</span>
													<span className="flex items-center gap-1">
														<Clock className="w-4 h-4" aria-hidden="true" />
														Updated {opportunity.lastUpdate}
													</span>
												</div>
											</div>
											<div className="flex gap-2">
												<Button asChild>
													<Link to={`/opportunities/${opportunity.id}`}>View Details</Link>
												</Button>
												<Button variant="outline">Withdraw</Button>
											</div>
										</div>
									</CardContent>
								</Card>
							))
						)}
					</TabsContent>

					{/* Recommended */}
					<TabsContent value="recommended">
						<Card>
							<CardHeader>
								<CardTitle>Recommended for You</CardTitle>
								<CardDescription>
									Based on your profile and saved opportunities
								</CardDescription>
							</CardHeader>
							<CardContent>
								<p className="text-neutral-600 mb-4">
									We're working on personalized recommendations. Check back soon!
								</p>
								<Button asChild>
									<Link to="/opportunities">Browse All Opportunities</Link>
								</Button>
							</CardContent>
						</Card>
					</TabsContent>
				</Tabs>
			</div>
		</section>
	);
};

export default Dashboard;
