import {
  getOpportunityById,
  type Opportunity,
} from '@/src/features/opportunities/services/opportunitiesService';
import api from '@/src/shared/services/api';

import { readSavedOpportunityIds } from '@/src/features/opportunities/utils/savedOpportunitiesStorage';

export type CandidateApplication = {
  id: number;
  opportunity_id: number;
  opportunity_title: string;
  organisation_name: string;
  ville: string;
  statut: string;
  submitted_at: string | null;
  cover_letter_url: string | null;
};

function normalizeApplication(item: unknown): CandidateApplication | null {
  if (!item || typeof item !== 'object') return null;

  const raw = item as Record<string, unknown>;
  const id = Number(raw.id);
  const opportunityId = Number(raw.opportunity_id);

  if (!Number.isInteger(id) || id <= 0 || !Number.isInteger(opportunityId) || opportunityId <= 0) {
    return null;
  }

  return {
    id,
    opportunity_id: opportunityId,
    opportunity_title: String(raw.opportunity_title || '').trim() || 'Untitled opportunity',
    organisation_name: String(raw.organisation_name || '').trim(),
    ville: String(raw.ville || '').trim(),
    statut: String(raw.statut || '').trim().toUpperCase() || 'UPDATED',
    submitted_at: raw.submitted_at ? String(raw.submitted_at) : null,
    cover_letter_url: raw.cover_letter_url ? String(raw.cover_letter_url) : null,
  };
}

export async function fetchMyApplications(): Promise<CandidateApplication[]> {
  const response = await api.get('/me/applications/');
  if (!Array.isArray(response.data)) return [];

  return response.data
    .map((item) => normalizeApplication(item))
    .filter((item): item is CandidateApplication => Boolean(item));
}

export async function withdrawMyApplication(applicationId: number): Promise<void> {
  await api.patch(`/me/applications/${applicationId}/withdraw/`, {});
}

export async function fetchSavedOpportunities(): Promise<Opportunity[]> {
  const savedIds = await readSavedOpportunityIds();
  if (!savedIds.length) return [];

  const results = await Promise.allSettled(savedIds.map((id) => getOpportunityById(id)));

  return results
    .map((result) => (result.status === 'fulfilled' ? result.value : null))
    .filter((item): item is Opportunity => Boolean(item));
}
