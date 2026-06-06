import { TUNISIAN_LOCATION_OPTIONS } from '../profile/profilePreferences.js';
import {
  ALLOWED_TENDER_DOCUMENT_EXTENSIONS,
  INTERNSHIP_DURATION_OPTIONS,
  INTERNSHIP_TYPE_OPTIONS,
  MAX_TENDER_DOCUMENT_FILE_SIZE_BYTES,
  SEASON_OPTIONS,
} from './opportunityPostConstants.js';

const INTERNSHIP_TYPE_VALUES = new Set(INTERNSHIP_TYPE_OPTIONS.map((option) => option.value));
const INTERNSHIP_DURATION_VALUES = new Set(INTERNSHIP_DURATION_OPTIONS.map((option) => option.value));
const SEASON_VALUES = new Set(SEASON_OPTIONS.map((option) => option.value));

export const splitSkills = (value) => {
  const seen = new Set();
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter((item) => {
      const key = item.toLocaleLowerCase();
      if (!item || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};

const parseLocalDate = (value) => {
  if (!value) return null;
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const isValidTime = (value) => /^\d{2}:\d{2}$/.test(String(value || '').trim());

const isPositiveIntegerText = (value) => {
  const text = String(value || '').trim();
  return !text || /^\d+$/.test(text);
};

const isValidPublicUrl = (value) => {
  const text = String(value || '').trim();
  if (!text) return true;
  try {
    const url = new URL(text);
    return ['http:', 'https:'].includes(url.protocol) && url.hostname.includes('.');
  } catch {
    return false;
  }
};

export const validateTenderDocumentFile = (file) => {
  if (!file) return 'Choose a document first.';
  const extension = String(file.name || '').split('.').pop()?.toLowerCase();
  if (!ALLOWED_TENDER_DOCUMENT_EXTENSIONS.includes(extension)) {
    return 'Use a PDF, DOCX, or DOC document.';
  }
  if (file.size > MAX_TENDER_DOCUMENT_FILE_SIZE_BYTES) {
    return 'Document must be 5 MB or smaller.';
  }
  return '';
};

const todayAtMidnight = () => {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
};

export const validateInternshipPostForm = (values) => {
  const errors = {};
  const skills = splitSkills(values.skills);
  const startDate = parseLocalDate(values.start_date);
  const deadline = parseLocalDate(values.deadline);
  const today = todayAtMidnight();

  if (values.title.trim().length < 5) {
    errors.title = 'Enter a clear internship title with at least 5 characters.';
  }
  if (!TUNISIAN_LOCATION_OPTIONS.includes(values.location)) {
    errors.location = 'Choose a valid Tunisian location.';
  }
  if (!INTERNSHIP_TYPE_VALUES.has(values.internship_type)) {
    errors.internship_type = 'Choose a valid internship type.';
  }
  if (!INTERNSHIP_DURATION_VALUES.has(values.duration)) {
    errors.duration = 'Choose a valid internship duration.';
  }
  if (!values.start_date || !startDate) {
    errors.start_date = 'Choose a valid start date.';
  } else if (startDate < today) {
    errors.start_date = 'Start date cannot be in the past.';
  }
  if (values.description.trim().length < 40) {
    errors.description = 'Add at least 40 characters describing the internship.';
  }
  if (skills.length > 15) {
    errors.skills = 'Use up to 15 skills.';
  }
  if (values.deadline && !deadline) {
    errors.deadline = 'Choose a valid application deadline.';
  } else if (deadline && deadline < today) {
    errors.deadline = 'Application deadline cannot be in the past.';
  }

  return { errors, skills };
};

export const validateSeasonalPostForm = (values) => {
  const errors = {};
  const skills = splitSkills(values.skills);
  const startDate = parseLocalDate(values.start_date);
  const endDate = parseLocalDate(values.end_date);
  const deadline = parseLocalDate(values.deadline);
  const today = todayAtMidnight();
  const salary = values.salary.trim();

  if (values.title.trim().length < 5) {
    errors.title = 'Enter a clear seasonal job title with at least 5 characters.';
  }
  if (!TUNISIAN_LOCATION_OPTIONS.includes(values.location)) {
    errors.location = 'Choose a valid Tunisian location.';
  }
  if (!SEASON_VALUES.has(values.season)) {
    errors.season = 'Choose a valid season.';
  }
  if (!values.start_date || !startDate) {
    errors.start_date = 'Choose a valid start date.';
  } else if (startDate < today) {
    errors.start_date = 'Start date cannot be in the past.';
  }
  if (!values.end_date || !endDate) {
    errors.end_date = 'Choose a valid end date.';
  } else if (endDate < today) {
    errors.end_date = 'End date cannot be in the past.';
  }
  if (startDate && endDate && endDate < startDate) {
    errors.end_date = 'End date must be after the start date.';
  }
  if (values.description.trim().length < 40) {
    errors.description = 'Add at least 40 characters describing the seasonal job.';
  }
  if (skills.length > 15) {
    errors.skills = 'Use up to 15 skills.';
  }
  if (salary && /(^|[\s:])-\s*\d/.test(salary)) {
    errors.salary = 'Salary cannot be negative.';
  }
  if (values.deadline && !deadline) {
    errors.deadline = 'Choose a valid application deadline.';
  } else if (deadline && deadline < today) {
    errors.deadline = 'Application deadline cannot be in the past.';
  }

  return { errors, skills };
};

export const validateTenderPostForm = (values) => {
  const errors = {};
  const deadline = parseLocalDate(values.deadline);
  const openingDate = parseLocalDate(values.opening_date);
  const executionStartDate = parseLocalDate(values.execution_start_date);
  const today = todayAtMidnight();

  if (values.title.trim().length < 5) {
    errors.title = 'Enter a clear tender object with at least 5 characters.';
  }
  if (!values.public_buyer.trim()) {
    errors.public_buyer = 'Public buyer is required.';
  }
  if (!TUNISIAN_LOCATION_OPTIONS.includes(values.location)) {
    errors.location = 'Choose a valid Tunisian execution region.';
  }
  if (!values.procedure.trim()) {
    errors.procedure = 'Procedure is required.';
  }
  if (!values.deadline || !deadline) {
    errors.deadline = 'Choose a valid reception deadline.';
  } else if (deadline < today) {
    errors.deadline = 'Reception deadline cannot be in the past.';
  }
  if (!isValidTime(values.deadline_time)) {
    errors.deadline_time = 'Use HH:MM format.';
  }
  if (values.description.trim().length < 40) {
    errors.description = 'Add at least 40 characters describing the tender scope.';
  }
  if (!isPositiveIntegerText(values.number_of_lots)) {
    errors.number_of_lots = 'Use a positive whole number.';
  }
  if (!isPositiveIntegerText(values.delai_validite)) {
    errors.delai_validite = 'Use a positive whole number of days.';
  }
  if (values.execution_start_date && !executionStartDate) {
    errors.execution_start_date = 'Choose a valid execution start date.';
  }
  if (values.opening_date && !openingDate) {
    errors.opening_date = 'Choose a valid opening date.';
  }
  if (values.opening_time && !isValidTime(values.opening_time)) {
    errors.opening_time = 'Use HH:MM format.';
  }

  const lots = values.lots
    .map((lot, index) => {
      const rawTitle = lot.lot.trim();
      const defaultTitle = `Lot ${index + 1}`;
      const meaningfulFields = [
        lot.objet,
        lot.quantite,
        lot.region,
        lot.caution,
      ].map((item) => String(item || '').trim());
      const titleIsCustom = rawTitle && rawTitle !== defaultTitle;

      return {
        lot: rawTitle || defaultTitle,
        hasMeaningfulValue: titleIsCustom || meaningfulFields.some(Boolean),
        objet: lot.objet.trim(),
        quantite: lot.quantite.trim(),
        region: lot.region.trim(),
        caution: lot.caution.trim(),
      };
    })
    .filter((lot) => lot.hasMeaningfulValue)
    .map(({ hasMeaningfulValue, ...lot }) => ({
      ...lot,
      objet: lot.objet.trim(),
      quantite: lot.quantite.trim(),
      region: lot.region.trim(),
      caution: lot.caution.trim(),
    }));

  lots.forEach((lot, index) => {
    if (!lot.objet) {
      errors.lots = `Lot ${index + 1}: object is required.`;
    }
  });

  const documents = values.documents
    .map((document) => ({
      type: document.type,
      url: document.url.trim(),
      label: document.label.trim(),
      filename: String(document.filename || '').trim(),
    }))
    .filter((document) => document.url);

  documents.forEach((document, index) => {
    if (!isValidPublicUrl(document.url)) {
      errors.documents = `Document ${index + 1}: enter a valid public URL.`;
    }
  });

  return { errors, lots, documents };
};
