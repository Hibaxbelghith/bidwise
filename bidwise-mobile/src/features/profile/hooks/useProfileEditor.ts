import { useCallback, useEffect, useMemo, useState } from 'react';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import {
  getProfileUpdateErrorMessage,
  updateProfile,
} from '@/src/features/profile/services/profileService';
import type { ProfileEditorState } from '@/src/features/profile/types';
import {
  buildProfileEditorState,
  buildProfileUpdatePayload,
} from '@/src/features/profile/utils/profileEditorState';
import {
  DEFAULT_COMPENSATION_PERIOD,
  normalizeLocations,
  normalizeTextLabel,
  validateProfileName,
  validateSalaryRange,
  validateYearsOfExperience,
} from '@/src/features/profile/utils/profileValidation';

const MAX_PREFERRED_LOCATIONS = 10;
const FALLBACK_SAVE_ERROR = 'Could not save your profile right now.';
const isCallsForTenderOnly = (values: string[]) =>
  values.length === 1 && values[0] === 'CALLS_FOR_TENDER';

export type ProfileEditorFieldErrors = {
  firstName?: string;
  lastName?: string;
  yearsOfExperience?: string;
  salaryRange?: string;
  preferredLocations?: string;
};

export function useProfileEditor() {
  const { user, loadUserProfile } = useAuth();
  const [editorState, setEditorState] = useState<ProfileEditorState>(() => buildProfileEditorState(user));
  const [fieldErrors, setFieldErrors] = useState<ProfileEditorFieldErrors>({});
  const [formError, setFormError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [locationInput, setLocationInput] = useState('');

  useEffect(() => {
    setEditorState(buildProfileEditorState(user));
  }, [user]);

  const initialStateKey = useMemo(() => JSON.stringify(buildProfileEditorState(user)), [user]);
  const currentStateKey = useMemo(() => JSON.stringify(editorState), [editorState]);
  const isDirty = initialStateKey !== currentStateKey;

  const salaryValidation = useMemo(
    () =>
      validateSalaryRange(
        editorState.formData.salaryMinExpectation,
        editorState.formData.salaryMaxExpectation,
        editorState.formData.salaryPeriod || DEFAULT_COMPENSATION_PERIOD,
      ),
    [editorState.formData.salaryMaxExpectation, editorState.formData.salaryMinExpectation, editorState.formData.salaryPeriod],
  );

  const setFormField = useCallback(
    <K extends keyof ProfileEditorState['formData']>(field: K, value: ProfileEditorState['formData'][K]) => {
      setEditorState((current) => ({
        ...current,
        formData: {
          ...current.formData,
          [field]: value,
        },
      }));
      setFieldErrors((current) => ({ ...current, [field]: '' }));
      setFormError('');
      setSuccessMessage('');
    },
    [],
  );

  const setStateField = useCallback(
    <K extends keyof Omit<ProfileEditorState, 'formData'>>(field: K, value: ProfileEditorState[K]) => {
      setEditorState((current) => ({
        ...current,
        [field]: value,
      }));
      setFieldErrors((current) => ({
        ...current,
        ...(field === 'preferredLocations' ? { preferredLocations: '' } : {}),
      }));
      setFormError('');
      setSuccessMessage('');
    },
    [],
  );

  const addPreferredLocation = useCallback((rawValue: string) => {
    const normalized = normalizeTextLabel(rawValue);
    if (!normalized) return;

    setEditorState((current) => {
      const nextLocations = normalizeLocations([...current.preferredLocations, normalized]).slice(0, MAX_PREFERRED_LOCATIONS);
      return {
        ...current,
        preferredLocations: nextLocations,
      };
    });
    setLocationInput('');
    setFieldErrors((current) => ({ ...current, preferredLocations: '' }));
    setFormError('');
    setSuccessMessage('');
  }, []);

  const removePreferredLocation = useCallback((location: string) => {
    setEditorState((current) => ({
      ...current,
      preferredLocations: current.preferredLocations.filter((item) => item !== location),
    }));
    setFieldErrors((current) => ({ ...current, preferredLocations: '' }));
    setFormError('');
    setSuccessMessage('');
  }, []);

  const validate = useCallback(() => {
    const nextFieldErrors: ProfileEditorFieldErrors = {};
    const tenderOnly = isCallsForTenderOnly(editorState.opportunityTypes);

    const firstNameValidation = validateProfileName(editorState.formData.firstName);
    const lastNameValidation = validateProfileName(editorState.formData.lastName);
    const yearsValidation = validateYearsOfExperience(editorState.formData.yearsOfExperience);

    if (firstNameValidation.error) nextFieldErrors.firstName = firstNameValidation.error;
    if (lastNameValidation.error) nextFieldErrors.lastName = lastNameValidation.error;
    if (!tenderOnly && yearsValidation.error) nextFieldErrors.yearsOfExperience = yearsValidation.error;
    if (!tenderOnly && salaryValidation.error) nextFieldErrors.salaryRange = salaryValidation.error;

    if (editorState.preferredLocations.length > MAX_PREFERRED_LOCATIONS) {
      nextFieldErrors.preferredLocations = `Choose up to ${MAX_PREFERRED_LOCATIONS} preferred locations.`;
    }

    setFieldErrors(nextFieldErrors);
    return {
      valid: Object.keys(nextFieldErrors).length === 0,
      firstNameValidation,
      lastNameValidation,
      yearsValidation,
    };
  }, [
    editorState.formData.firstName,
    editorState.formData.lastName,
    editorState.formData.yearsOfExperience,
    editorState.opportunityTypes,
    editorState.preferredLocations.length,
    salaryValidation.error,
  ]);

  const handleSave = useCallback(async () => {
    const { valid, firstNameValidation, lastNameValidation, yearsValidation } = validate();
    if (!valid) return false;

    setSaving(true);
    setFormError('');
    setSuccessMessage('');

    try {
      const basePayload = buildProfileUpdatePayload(editorState);
      const tenderOnly = isCallsForTenderOnly(editorState.opportunityTypes);
      const payload = tenderOnly
        ? {
            prenom: firstNameValidation.value || null,
            nom: lastNameValidation.value || null,
            opportunity_types: ['CALLS_FOR_TENDER'],
            preferred_locations: editorState.preferredLocations,
            domaines_interet: [],
            competences: [],
            niveau_experience: null,
            annees_experience: null,
            target_roles: [],
            work_mode_preferences: [],
            employment_types: [],
            compensation_expectation: null,
            compensation_min_expectation: null,
            compensation_max_expectation: null,
            compensation_currency: 'TND',
            compensation_period: DEFAULT_COMPENSATION_PERIOD,
            profile_visibility: editorState.profileVisibility,
          }
        : {
            ...basePayload,
            prenom: firstNameValidation.value || null,
            nom: lastNameValidation.value || null,
            annees_experience: yearsValidation.value,
            compensation_expectation: salaryValidation.min ?? salaryValidation.max,
            compensation_min_expectation: salaryValidation.min,
            compensation_max_expectation: salaryValidation.max,
            compensation_currency: 'TND',
            compensation_period: editorState.formData.salaryPeriod || DEFAULT_COMPENSATION_PERIOD,
          };

      setLoading(true);
      await updateProfile(payload);
      await loadUserProfile();
      setSuccessMessage('Profile updated successfully.');
      return true;
    } catch (error) {
      setFormError(getProfileUpdateErrorMessage(error, FALLBACK_SAVE_ERROR));
      return false;
    } finally {
      setSaving(false);
      setLoading(false);
    }
  }, [editorState, loadUserProfile, salaryValidation.max, salaryValidation.min, validate]);

  return {
    editorState,
    fieldErrors,
    formError,
    successMessage,
    loading,
    saving,
    isDirty,
    locationInput,
    setLocationInput,
    salaryValidation,
    setFormField,
    setStateField,
    addPreferredLocation,
    removePreferredLocation,
    handleSave,
    refreshProfile: loadUserProfile,
  };
}
