import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getOrganizationOpportunity } from '../services/organizationService.js';

const EDIT_PATHS = {
  EMPLOI: '/organization/post/job',
  STAGE: '/organization/post/internship',
  SAISONNIER: '/organization/post/seasonal',
  PROJET: '/organization/post/call-for-tender',
};

const foldValue = (value) => String(value || '')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .trim()
  .toLowerCase();

export const normalizeOptionValue = (value, options, fallback = '') => {
  const key = foldValue(value);
  if (!key) return fallback;
  const match = options.find((option) => {
    const optionValue = typeof option === 'string' ? option : option.value;
    const optionLabel = typeof option === 'string' ? option : option.label;
    return foldValue(optionValue) === key || foldValue(optionLabel) === key;
  });
  return match ? (typeof match === 'string' ? match : match.value) : fallback;
};

export const normalizeDateInputValue = (value) => {
  const text = String(value || '').trim();
  if (!text) return '';
  const match = text.match(/^\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : '';
};

export const normalizeInternshipType = (value) => {
  const aliases = {
    graduation: 'GRADUATION_PROJECT',
    'graduation type': 'GRADUATION_PROJECT',
    'graduation project': 'GRADUATION_PROJECT',
    pfe: 'GRADUATION_PROJECT',
    training: 'TRAINING',
    summer: 'SUMMER',
  };
  return aliases[foldValue(value)] || normalizeOptionValue(value, [
    { value: 'GRADUATION_PROJECT', label: 'Graduation internship' },
    { value: 'TRAINING', label: 'Training internship' },
    { value: 'SUMMER', label: 'Summer internship' },
  ], 'GRADUATION_PROJECT');
};

export const organizationOpportunityEditPath = (opportunity) => {
  const base = EDIT_PATHS[opportunity?.type];
  return base && opportunity?.id ? `${base}/${opportunity.id}/edit` : null;
};

const useOrganizationOpportunityEdit = (expectedType) => {
  const { opportunityId } = useParams();
  const isEditing = Boolean(opportunityId);
  const [opportunity, setOpportunity] = useState(null);
  const [isLoading, setIsLoading] = useState(isEditing);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (!isEditing) return undefined;
    const controller = new AbortController();
    setIsLoading(true);
    setLoadError('');

    getOrganizationOpportunity(opportunityId, { signal: controller.signal })
      .then((item) => {
        if (controller.signal.aborted) return;
        if (item.type !== expectedType) {
          setLoadError('This opportunity does not match this form type.');
        } else {
          setOpportunity(item);
        }
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        const message = error?.response?.status === 404
          ? 'This opportunity could not be found in your organization workspace.'
          : 'Unable to load this opportunity. Please return to the dashboard and try again.';
        setLoadError(message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, [expectedType, isEditing, opportunityId]);

  return useMemo(() => ({
    opportunityId,
    isEditing,
    opportunity,
    isLoading,
    loadError,
  }), [isEditing, isLoading, loadError, opportunity, opportunityId]);
};

export default useOrganizationOpportunityEdit;
