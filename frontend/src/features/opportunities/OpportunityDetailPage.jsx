import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Bookmark,
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Lock,
} from 'lucide-react';

import { Badge } from '../../components/ui/badge.jsx';
import { Button } from '../../components/ui/button.jsx';
import { Separator } from '../../components/ui/separator.jsx';
import { useAuth } from '../auth/AuthContext.jsx';
import { useOpportunityDetail, useSimilarOpportunities } from './useOpportunities';
import { dedupeSimilarOpportunities, formatSimilarityScore } from './utils/similarity.js';
import {
  buildAIDraft,
  buildDescriptionMarkup,
  buildDescriptionText,
  buildMatchBullets,
  DESCRIPTION_COLLAPSE_HEIGHT,
  formatExperienceLabel,
  formatOrganizationLabel,
  getLanguagePreview,
  getProjectDocuments,
  getSkills,
  getSemanticMatchScore,
  QUICK_SCAN_SKILLS_LIMIT,
  readSavedOpportunityIds,
  TYPE_LABELS,
  writeSavedOpportunityIds,
} from './OpportunityDetail.utils';
import OpportunityDetailSkeleton from './OpportunityDetailSkeleton.jsx';
import OpportunityHeader from './OpportunityHeader.jsx';
import OpportunityMeta from './OpportunityMeta.jsx';
import OpportunityExtraData from './OpportunityExtraData.jsx';
import OpportunityDocuments from './OpportunityDocuments.jsx';
import OpportunitySnapshot from './OpportunitySnapshot.jsx';
import LockPreviewCard from './LockPreviewCard.jsx';

const OpportunityDetail = () => {
  const { id } = useParams();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const { opportunity, loading, error } = useOpportunityDetail(id);

  const isUserAuthenticated = !authLoading && isAuthenticated;

  const { similarOpportunities, loading: similarLoading, error: similarError } = useSimilarOpportunities(
    opportunity?.id,
    8,
    Boolean(opportunity?.id && isUserAuthenticated)
  );

  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [showAllSkills, setShowAllSkills] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    setIsDescriptionExpanded(false);
    setShowAllSkills(false);
  }, [opportunity?.id]);

  useEffect(() => {
    if (!opportunity?.id || !isUserAuthenticated) {
      setIsSaved(false);
      return;
    }

    const savedIds = readSavedOpportunityIds();
    setIsSaved(savedIds.has(String(opportunity.id)));
  }, [opportunity?.id, isUserAuthenticated]);

  const dedupedSimilar = useMemo(() => {
    if (!isUserAuthenticated) return [];

    return dedupeSimilarOpportunities(similarOpportunities).filter(
      (item) => Number(item?.id) !== Number(opportunity?.id)
    );
  }, [isUserAuthenticated, similarOpportunities, opportunity?.id]);

  const semanticMatchScore = useMemo(() => {
    if (!isUserAuthenticated) return null;
    return getSemanticMatchScore(dedupedSimilar);
  }, [dedupedSimilar, isUserAuthenticated]);

  if (loading) {
    return <OpportunityDetailSkeleton />;
  }

  if (error || !opportunity) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
        <Link to="/opportunities" className="inline-flex items-center gap-2 text-neutral-600">
          <ArrowLeft className="h-4 w-4" />
          Back to opportunities
        </Link>
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
          {error || 'Opportunity not found'}
        </div>
      </div>
    );
  }

  const sourceUrl = String(opportunity.source_item_url || '').trim();
  const descriptionMarkup = buildDescriptionMarkup(opportunity);
  const descriptionText = buildDescriptionText(opportunity);
  const isLongDescription = descriptionText.length > 480;
  const isProject = opportunity.type_opportunite === 'PROJET';
  const extraData =
    opportunity?.extra_data && typeof opportunity.extra_data === 'object' ? opportunity.extra_data : {};
  const hasExtraData = Object.keys(extraData).length > 0;
  const structuredProjectData =
    extraData?.structured && typeof extraData.structured === 'object' ? extraData.structured : {};
  const projectLots = Array.isArray(extraData.lots) ? extraData.lots.filter(Boolean) : [];
  const projectDocuments = getProjectDocuments(opportunity);
  const hasProjectDocuments = Boolean(extraData.has_pdf) || projectDocuments.length > 0;
  const skills = getSkills(opportunity);
  const visibleSkills = showAllSkills ? skills : skills.slice(0, QUICK_SCAN_SKILLS_LIMIT);
  const hiddenSkillsCount = Math.max(0, skills.length - QUICK_SCAN_SKILLS_LIMIT);

  const salaryLabel = String(opportunity.salary || '').trim();
  const locationLabel = String(opportunity.ville || '').trim();
  const projectRegionLabel =
    String(extraData.region || extraData.region_execution || opportunity.ville || '').trim();
  const contractLabel = String(opportunity.contract_type || '').trim();
  const availabilityLabel = String(opportunity.availability || '').trim();
  const educationLabel = String(opportunity.education_level || '').trim();
  const experienceLabel = formatExperienceLabel(opportunity);
  const languagesLabel = getLanguagePreview(opportunity);
  const projectProcedureLabel =
    String(structuredProjectData.procedure || extraData.procedure || '').trim();
  const projectFinancementLabel =
    String(structuredProjectData.financement || extraData.financement || '').trim();
  const projectTypeCommandeLabel =
    String(structuredProjectData.type_commande || extraData.type_commande || '').trim();
  const projectDelaiValiditeLabel =
    String(structuredProjectData.delai_validite || extraData.delai_validite || '').trim();
  const projectCautionLabel = String(
    extraData.caution ||
      projectLots.find((lot) => String(lot?.caution || '').trim())?.caution ||
      '',
  ).trim();
  const primaryActionLabel = isProject ? 'Open source' : 'Apply';

  const matchBullets = buildMatchBullets(opportunity, semanticMatchScore);
  const aiDraft = buildAIDraft(opportunity);

  const handleApply = () => {
    if (!isUserAuthenticated || !sourceUrl) return;
    window.open(sourceUrl, '_blank', 'noopener,noreferrer');
  };

  const handleSave = () => {
    if (!isUserAuthenticated) return;

    const opportunityId = String(opportunity.id);
    const savedIds = readSavedOpportunityIds();
    const nextSaved = !savedIds.has(opportunityId);

    if (nextSaved) {
      savedIds.add(opportunityId);
    } else {
      savedIds.delete(opportunityId);
    }

    writeSavedOpportunityIds(savedIds);
    setIsSaved(nextSaved);
  };

  const canApply = isUserAuthenticated && Boolean(sourceUrl);

  return (
    <div className="min-h-screen bg-neutral-50 pb-32">
      <OpportunityHeader
        opportunity={opportunity}
        isUserAuthenticated={isUserAuthenticated}
        semanticMatchScore={semanticMatchScore}
        projectRegionLabel={projectRegionLabel}
      />

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <OpportunityMeta
          opportunity={opportunity}
          isProject={isProject}
          projectRegionLabel={projectRegionLabel}
          projectProcedureLabel={projectProcedureLabel}
          projectFinancementLabel={projectFinancementLabel}
          salaryLabel={salaryLabel}
          locationLabel={locationLabel}
          contractLabel={contractLabel}
          availabilityLabel={availabilityLabel}
          educationLabel={educationLabel}
        />

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-6">
            <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-neutral-900">Description</h2>
                {isLongDescription ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsDescriptionExpanded((prev) => !prev)}
                  >
                    {isDescriptionExpanded ? (
                      <>
                        Show less <ChevronUp className="h-4 w-4" />
                      </>
                    ) : (
                      <>
                        Show more <ChevronDown className="h-4 w-4" />
                      </>
                    )}
                  </Button>
                ) : null}
              </div>

              <div
                className="relative rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3"
                style={
                  isDescriptionExpanded || !isLongDescription
                    ? undefined
                    : { maxHeight: DESCRIPTION_COLLAPSE_HEIGHT, overflow: 'hidden' }
                }
              >
                <div
                  className="whitespace-pre-wrap text-sm leading-7 text-neutral-700"
                  dangerouslySetInnerHTML={{ __html: descriptionMarkup }}
                />

                {!isDescriptionExpanded && isLongDescription ? (
                  <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-neutral-50 to-transparent" />
                ) : null}
              </div>
            </section>

            <OpportunityExtraData
              opportunity={opportunity}
              isProject={isProject}
              hasExtraData={hasExtraData}
              extraData={extraData}
              structuredProjectData={structuredProjectData}
              projectRegionLabel={projectRegionLabel}
              projectProcedureLabel={projectProcedureLabel}
              projectFinancementLabel={projectFinancementLabel}
              projectTypeCommandeLabel={projectTypeCommandeLabel}
              projectDelaiValiditeLabel={projectDelaiValiditeLabel}
              projectCautionLabel={projectCautionLabel}
              projectLots={projectLots}
            />

            {!isProject && projectDocuments.length ? (
              <OpportunityDocuments documents={projectDocuments} />
            ) : null}

            {isProject && hasProjectDocuments ? (
              <div className="mt-5">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-base font-semibold text-neutral-900">Documents</h3>
                  <p className="text-xs text-neutral-500">
                    Open the official source files attached to this tender.
                  </p>
                </div>
                <OpportunityDocuments documents={projectDocuments} />
              </div>
            ) : null}

            {!isProject ? (
              <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <h2 className="text-lg font-semibold text-neutral-900">Skills</h2>
                  {skills.length > QUICK_SCAN_SKILLS_LIMIT ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowAllSkills((prev) => !prev)}
                    >
                      {showAllSkills ? 'Show less' : `+${hiddenSkillsCount} more`}
                    </Button>
                  ) : null}
                </div>

                {visibleSkills.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {visibleSkills.map((skill) => (
                      <Badge key={skill} variant="outline" className="bg-white font-medium">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-neutral-600">No structured skills provided.</p>
                )}
              </section>
            ) : null}

            {isUserAuthenticated ? (
              <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-lg font-semibold text-neutral-900">AI Insights</h2>

                <div className="space-y-3">
                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Match score</p>
                    <div className="mt-2 flex items-center gap-3">
                      <p className="text-3xl font-bold text-neutral-900">
                        {semanticMatchScore !== null ? `${semanticMatchScore}%` : 'N/A'}
                      </p>
                      <div className="h-2 w-24 overflow-hidden rounded-full bg-neutral-200">
                        <div
                          className="h-full rounded-full bg-blue-600"
                          style={{ width: `${semanticMatchScore ?? 0}%` }}
                        />
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-neutral-600">
                      Based on semantic similarity between this opportunity and related listings.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                      Why this matches you
                    </p>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-neutral-800">
                      {matchBullets.map((bullet) => (
                        <li key={bullet}>{bullet}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                      AI-generated application draft
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-neutral-800">{aiDraft}</p>
                    <p className="mt-2 text-xs text-neutral-600">
                      CV and cover letter automation will expand in Sprint 3.
                    </p>
                  </div>
                </div>
              </section>
            ) : (
              <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
                <h2 className="mb-2 text-lg font-semibold text-neutral-900">Unlock AI Intelligence</h2>
                <p className="mb-4 text-sm leading-6 text-neutral-600">
                  Core opportunity data stays open. Login to unlock match score, recommendation
                  intelligence, and AI application support.
                </p>

                <div className="grid gap-3 md:grid-cols-3">
                  <LockPreviewCard
                    title="Match score"
                    body="See a numeric fit score to quickly prioritize the best opportunities."
                  />
                  <LockPreviewCard
                    title="Why this matches"
                    body="Understand fit drivers such as skills overlap, experience, and location."
                  />
                  <LockPreviewCard
                    title="AI draft assistant"
                    body="Generate a tailored application draft and iterate faster."
                  />
                </div>

                <Button asChild className="mt-4 w-full sm:w-auto">
                  <Link to="/login">Login to unlock AI features</Link>
                </Button>
              </section>
            )}

            <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-neutral-900">Similar opportunities</h2>
                <Badge variant="outline">{isUserAuthenticated ? 'Available' : 'Locked preview'}</Badge>
              </div>

              {isUserAuthenticated ? (
                <>
                  {similarLoading ? (
                    <div className="space-y-3">
                      <div className="h-16 animate-pulse rounded-2xl border border-neutral-200 bg-neutral-100" />
                      <div className="h-16 animate-pulse rounded-2xl border border-neutral-200 bg-neutral-100" />
                    </div>
                  ) : null}

                  {!similarLoading && similarError ? (
                    <p className="text-sm text-neutral-600">
                      Similar opportunities are currently unavailable. Please retry later.
                    </p>
                  ) : null}

                  {!similarLoading && !similarError && !dedupedSimilar.length ? (
                    <p className="text-sm text-neutral-600">No similar opportunities found.</p>
                  ) : null}

                  {!similarLoading && !similarError && dedupedSimilar.length ? (
                    <div className="space-y-3">
                      {dedupedSimilar.map((similarItem) => {
                        const score = formatSimilarityScore(similarItem?.similarity_score);
                        const companyName =
                          String(similarItem?.organisation_nom || '').trim() ||
                          'BidWise recommendation';

                        return (
                          <Link
                            key={similarItem.id}
                            to={`/opportunities/${similarItem.id}`}
                            className="block rounded-2xl border border-neutral-200 bg-white px-4 py-3 transition-colors hover:border-blue-300"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <p className="font-medium text-neutral-900">
                                  {similarItem.titre || `Opportunity #${similarItem.id}`}
                                </p>
                                <p className="mt-1 text-xs text-neutral-600">{companyName}</p>
                              </div>
                              <Badge variant="secondary">Match {score.percentage}%</Badge>
                            </div>
                          </Link>
                        );
                      })}
                    </div>
                  ) : null}
                </>
              ) : (
                <>
                  <div className="space-y-3">
                    <LockPreviewCard
                      title="Ranked recommendations"
                      body="Get a personalized ranking of similar opportunities based on your profile."
                    />
                    <LockPreviewCard
                      title="One-click comparison"
                      body="Compare opportunities side by side to pick the strongest applications."
                    />
                    <LockPreviewCard
                      title="Continuous discovery"
                      body="Receive fresh similar opportunities as new listings are indexed."
                    />
                  </div>

                  <Button asChild className="mt-4 w-full sm:w-auto" variant="outline">
                    <Link to="/login">Login to view similar opportunities</Link>
                  </Button>
                </>
              )}
            </section>
          </div>

          <aside className="hidden lg:sticky lg:top-24 lg:block lg:self-start">
            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
              <h3 className="mb-4 text-base font-semibold text-neutral-900">Opportunity snapshot</h3>

              <OpportunitySnapshot
                opportunity={opportunity}
                isProject={isProject}
                typeLabel={TYPE_LABELS[opportunity.type_opportunite] || opportunity.type_opportunite || 'N/A'}
                projectRegionLabel={projectRegionLabel}
                projectProcedureLabel={projectProcedureLabel}
                projectFinancementLabel={projectFinancementLabel}
                projectTypeCommandeLabel={projectTypeCommandeLabel}
                projectCautionLabel={projectCautionLabel}
                organizationLabel={formatOrganizationLabel(opportunity)}
                contractLabel={contractLabel}
                availabilityLabel={availabilityLabel}
                experienceLabel={experienceLabel}
                educationLabel={educationLabel}
                languagesLabel={languagesLabel}
              />

              <Separator className="my-5" />

              {isUserAuthenticated ? (
                <div className="space-y-2">
                  <Button onClick={handleApply} disabled={!canApply} className="w-full">
                    {primaryActionLabel}
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" onClick={handleSave} className="w-full">
                    {isSaved ? (
                      <>
                        Saved
                        <Check className="h-4 w-4" />
                      </>
                    ) : (
                      <>
                        Save
                        <Bookmark className="h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Button asChild className="w-full">
                    <Link to="/login">Login to unlock actions</Link>
                  </Button>
                  <Button variant="outline" disabled className="w-full">
                    <Lock className="h-4 w-4" />
                    Save and Apply locked
                  </Button>
                </div>
              )}
            </div>
          </aside>
        </div>
      </main>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-white/95 backdrop-blur lg:hidden">
        <div className="mx-auto flex max-w-6xl gap-3 px-4 py-3 sm:px-6 lg:px-8">
          {isUserAuthenticated ? (
            <>
              <Button variant="outline" onClick={handleSave} className="flex-1">
                {isSaved ? (
                  <>
                    Saved
                    <Check className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    Save
                    <Bookmark className="h-4 w-4" />
                  </>
                )}
              </Button>
              <Button onClick={handleApply} disabled={!canApply} className="flex-1">
                {primaryActionLabel}
                <ExternalLink className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <Button asChild className="flex-1">
                <Link to="/login">Login to unlock</Link>
              </Button>
              <Button variant="outline" disabled className="flex-1">
                <Lock className="h-4 w-4" />
                Actions locked
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default OpportunityDetail;
