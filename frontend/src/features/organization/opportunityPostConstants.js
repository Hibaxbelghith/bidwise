export const FIELD_CLASS =
  'h-11 rounded-xl border-neutral-300 bg-white text-sm focus-visible:border-blue-500 focus-visible:ring-[3px] focus-visible:ring-blue-500/20';

export const WORK_MODE_OPTIONS = [
  'On site',
  'Hybrid',
  'Remote',
  'Full time',
  'Part time',
];

export const INTERNSHIP_TYPE_OPTIONS = [
  { value: 'GRADUATION_PROJECT', label: 'Graduation internship' },
  { value: 'TRAINING', label: 'Training internship' },
  { value: 'SUMMER', label: 'Summer internship' },
];

export const INTERNSHIP_DURATION_OPTIONS = [
  { value: '1_MONTH', label: '1 month' },
  { value: '2_MONTHS', label: '2 months' },
  { value: '3_MONTHS', label: '3 months' },
  { value: '4_6_MONTHS', label: '4 to 6 months' },
  { value: '6_PLUS_MONTHS', label: '6+ months' },
];

export const INTERNSHIP_EDUCATION_OPTIONS = [
  'Bac+2',
  'Bac+3',
  'Bac+4',
  'Bac+5',
  'Engineering student',
  'Business school student',
  'Open to students',
];

export const SEASON_OPTIONS = [
  { value: 'SUMMER', label: 'Summer season' },
  { value: 'WINTER', label: 'Winter season' },
  { value: 'RAMADAN', label: 'Ramadan season' },
  { value: 'HOLIDAY', label: 'Holiday period' },
  { value: 'EVENT', label: 'Event period' },
  { value: 'OTHER', label: 'Other seasonal need' },
];

export const TENDER_PROCEDURE_OPTIONS = [
  "Appel d'offres ouvert",
  "Appel d'offres restreint",
  'Consultation',
  'Procédure négociée',
];

export const TENDER_DOCUMENT_TYPES = [
  { value: 'cahier_des_charges', label: 'Cahier des charges' },
  { value: 'avis_appel_offres', label: "Avis d'appel d'offres" },
  { value: 'autres', label: 'Other document' },
];

export const MAX_TENDER_DOCUMENT_FILE_SIZE_BYTES = 5 * 1024 * 1024;
export const ALLOWED_TENDER_DOCUMENT_EXTENSIONS = ['pdf', 'docx', 'doc'];
export const ALLOWED_TENDER_DOCUMENT_ACCEPT =
  '.pdf,.docx,.doc,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document';
