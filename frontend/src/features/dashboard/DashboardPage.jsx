import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { Briefcase, Clock, Bookmark, Building2, MapPin, Calendar, TrendingUp } from 'lucide-react';
import ApplicationsList from './components/ApplicationsList.jsx';
import useMyApplications from './hooks/useMyApplications.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { useLanguage } from '../../i18n/LanguageContext.jsx';
import { getOpportunityById } from '../opportunities/services/opportunitiesService.js';
import { buildOpportunityBrowseCardViewModel } from '../opportunities/viewModels/opportunityList.vm.js';
import {
	getSavedOpportunityIds,
	listenSavedOpportunityChanges,
	removeSavedOpportunity,
} from '../opportunities/utils/savedOpportunityStorage.js';

const normalizeSavedOpportunity = (opportunity) => ({
	id: opportunity.id,
	viewModel: buildOpportunityBrowseCardViewModel(opportunity, true),
});

const isCallsForTenderOnlyProfile = (profile) => {
	const types = Array.isArray(profile?.opportunity_types) ? profile.opportunity_types : [];
	return types.length === 1 && types[0] === 'CALLS_FOR_TENDER';
};

const Dashboard = () => {
	const { user } = useAuth();
	const { t } = useLanguage();
	const tenderOnly = isCallsForTenderOnlyProfile(user?.profil);
	const { applications, isLoading, error, withdraw } = useMyApplications({ enabled: !tenderOnly });
	const [savedOpportunities, setSavedOpportunities] = useState([]);
	const [savedLoading, setSavedLoading] = useState(true);
	const [savedError, setSavedError] = useState('');

	const loadSavedOpportunities = useCallback(async () => {
		const savedIds = getSavedOpportunityIds();

		if (savedIds.length === 0) {
			setSavedOpportunities([]);
			setSavedLoading(false);
			setSavedError('');
			return;
		}

		try {
			setSavedLoading(true);
			setSavedError('');

			const results = await Promise.allSettled(
				savedIds.map((id) => getOpportunityById(id)),
			);

			const opportunities = results
				.filter((result) => result.status === 'fulfilled' && result.value?.id)
				.map((result) => normalizeSavedOpportunity(result.value));

			setSavedOpportunities(opportunities);
		} catch {
			setSavedError(t('dashboard.unableLoadSaved'));
			setSavedOpportunities([]);
		} finally {
			setSavedLoading(false);
		}
	}, [t]);

	useEffect(() => {
		loadSavedOpportunities();
		return listenSavedOpportunityChanges(loadSavedOpportunities);
	}, [loadSavedOpportunities]);

	const savedCount = savedOpportunities.length;
	const appliedCount = useMemo(() => applications.length, [applications.length]);

	const handleRemoveSaved = (opportunityId) => {
		removeSavedOpportunity(opportunityId);
		setSavedOpportunities((current) =>
			current.filter((opportunity) => String(opportunity.id) !== String(opportunityId)),
		);
	};

	return (
		<section className="bg-neutral-50" aria-labelledby="dashboard-heading">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
				{/* Header */}
				<div className="mb-8">
					<h1 id="dashboard-heading" className="text-3xl font-bold text-neutral-900 mb-2">{t('dashboard.title')}</h1>
					<p className="text-neutral-600">
						{tenderOnly
							? t('dashboard.tenderSubtitle')
							: t('dashboard.subtitle')}
					</p>
				</div>

				{/* Stats Cards - Pleine largeur avec 3 cartes */}
				<div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8" role="region" aria-label={t('dashboard.statistics')}>
					{/* Carte 1: Sauvegardés */}
					<Card className="w-full">
						<CardHeader className="pb-3">
							<CardTitle className="text-sm font-medium text-neutral-600">
								{tenderOnly ? t('dashboard.savedTenders') : t('dashboard.saved')}
							</CardTitle>
						</CardHeader>
						<CardContent>
							<div className="flex items-center justify-between">
								<p className="text-3xl font-bold text-neutral-900">{savedCount}</p>
								<Bookmark className="w-8 h-8 text-blue-600" aria-hidden="true" />
							</div>
						</CardContent>
					</Card>

					{/* Carte 2: Candidatures (uniquement si pas tenderOnly) */}
					{!tenderOnly ? (
						<Card className="w-full">
							<CardHeader className="pb-3">
								<CardTitle className="text-sm font-medium text-neutral-600">{t('dashboard.applied')}</CardTitle>
							</CardHeader>
							<CardContent>
								<div className="flex items-center justify-between">
									<p className="text-3xl font-bold text-neutral-900">{appliedCount}</p>
									<Briefcase className="w-8 h-8 text-blue-600" aria-hidden="true" />
								</div>
							</CardContent>
						</Card>
					) : (
						/* Si tenderOnly, on affiche une carte vide ou on étend la première */
						<Card className="w-full opacity-0 invisible">
							<CardHeader className="pb-3">
								<CardTitle className="text-sm font-medium text-neutral-600">Placeholder</CardTitle>
							</CardHeader>
							<CardContent>
								<div className="flex items-center justify-between">
									<p className="text-3xl font-bold text-neutral-900">0</p>
								</div>
							</CardContent>
						</Card>
					)}

					{/* Carte 3: Vues du profil (uniquement si pas tenderOnly) */}
					{!tenderOnly ? (
						<Card className="w-full">
							<CardHeader className="pb-3">
								<CardTitle className="text-sm font-medium text-neutral-600">{t('dashboard.profileViews')}</CardTitle>
							</CardHeader>
							<CardContent>
								<div className="flex items-center justify-between">
									<p className="text-3xl font-bold text-neutral-900">24</p>
									<TrendingUp className="w-8 h-8 text-blue-600" aria-hidden="true" />
								</div>
							</CardContent>
						</Card>
					) : null}
				</div>

				{/* Main Content */}
				<Tabs defaultValue="saved" className="space-y-6">
					{!tenderOnly ? (
						<TabsList aria-label={t('dashboard.categories')}>
							<TabsTrigger value="saved">{t('dashboard.savedOpportunities')}</TabsTrigger>
							<TabsTrigger value="applied">{t('dashboard.applications')}</TabsTrigger>
						</TabsList>
					) : null}

					{/* Saved Opportunities */}
					<TabsContent value="saved" className="space-y-4">
						{savedLoading ? (
							<Card>
								<CardContent className="py-12 text-center">
									<p className="text-neutral-600">{t('dashboard.loadingSaved')}</p>
								</CardContent>
							</Card>
						) : savedError ? (
							<Card>
								<CardContent className="py-12 text-center">
									<p className="text-red-600 mb-4">{savedError}</p>
									<Button type="button" variant="outline" onClick={loadSavedOpportunities}>
										{t('dashboard.tryAgain')}
									</Button>
								</CardContent>
							</Card>
						) : savedOpportunities.length === 0 ? (
							<Card>
								<CardContent className="py-12 text-center">
									<Bookmark className="w-12 h-12 text-neutral-300 mx-auto mb-4" aria-hidden="true" />
									<p className="text-neutral-600 mb-4">
										{tenderOnly ? t('dashboard.noSavedTenders') : t('dashboard.noSavedOpportunities')}
									</p>
									<Button asChild>
										<Link to={tenderOnly ? '/opportunities?type=PROJET' : '/opportunities'}>
											{tenderOnly ? t('dashboard.browseTenders') : t('dashboard.browseOpportunities')}
										</Link>
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
														{opportunity.viewModel.title}
													</Link>
													<Badge>{opportunity.viewModel.typeLabel}</Badge>
													<Badge>
														{opportunity.viewModel.statusLabel}
													</Badge>
												</div>
												<div className="flex items-center gap-4 text-sm text-neutral-600 mb-3">
													{opportunity.viewModel.organizationLabel ? (
														<span className="flex items-center gap-1">
															<Building2 className="w-4 h-4" />
															{opportunity.viewModel.organizationLabel}
														</span>
													) : null}
													{opportunity.viewModel.locationLabel ? (
														<span className="flex items-center gap-1">
															<MapPin className="w-4 h-4" />
															{opportunity.viewModel.locationLabel}
														</span>
													) : null}
													{opportunity.viewModel.salaryLabel ? (
														<span className="flex items-center gap-1">
															{opportunity.viewModel.salaryLabel}
														</span>
													) : null}
												</div>
												<div className="flex flex-wrap gap-2 mb-3">
													{opportunity.viewModel.skillsPreview.map((tag) => (
														<Badge key={tag} variant="secondary">
															{tag}
														</Badge>
													))}
												</div>
												{opportunity.viewModel.deadlineDateLabel ? (
													<p className="text-sm text-neutral-500">
														{t('dashboard.deadline', { date: opportunity.viewModel.deadlineDateLabel })}
													</p>
												) : null}
											</div>
											<div className="flex gap-2">
												<Button asChild>
													<Link to={`/opportunities/${opportunity.id}`}>{t('dashboard.view')}</Link>
												</Button>
												<Button
													type="button"
													variant="outline"
													onClick={() => handleRemoveSaved(opportunity.id)}
												>
													{t('dashboard.remove')}
												</Button>
											</div>
										</div>
									</CardContent>
								</Card>
							))
						)}
					</TabsContent>

					{/* Applied Opportunities */}
					{!tenderOnly ? (
						<TabsContent value="applied" className="space-y-4">
							<ApplicationsList
								applications={applications}
								isLoading={isLoading}
								error={error}
								onWithdraw={withdraw}
							/>
						</TabsContent>
					) : null}
				</Tabs>
			</div>
		</section>
	);
};

export default Dashboard;