export const getSourceName = (source) => {
  if (!source) return '';
  if (typeof source === 'string') return source;
  if (typeof source === 'object') return source.nom || '';
  return '';
};

export const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).format(date);
};

export const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

export const statusClassName = (status) => {
  const value = String(status || '').toLowerCase();
  if (value === 'active') return 'border-green-200 bg-green-50 text-green-700';
  if (value === 'pending_review') return 'border-blue-200 bg-blue-50 text-blue-700';
  if (value === 'rejected') return 'border-red-200 bg-red-50 text-red-700';
  if (value === 'archivee' || value === 'archived') return 'border-neutral-200 bg-neutral-100 text-neutral-700';
  if (value === 'expiree' || value === 'expired') return 'border-yellow-200 bg-yellow-50 text-yellow-700';
  return 'border-neutral-200 bg-white text-neutral-700';
};

export const sourceClassName = (source) => {
  const value = getSourceName(source).toLowerCase();
  if (value.includes('linkedin')) return 'border-blue-200 bg-blue-50 text-blue-700';
  if (value.includes('keejob')) return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  return 'border-neutral-200 bg-neutral-50 text-neutral-700';
};

export const typeLabel = (type) => {
  const value = String(type || '').toUpperCase();
  if (value === 'EMPLOI') return 'Job';
  if (value === 'STAGE') return 'Internship';
  if (value === 'SAISONNIER') return 'Seasonal';
  if (value === 'PROJET') return 'Call for tender';
  return type || 'Unknown';
};

export const statusLabel = (status) => {
  const value = String(status || '').toUpperCase();
  if (value === 'ACTIVE') return 'Active';
  if (value === 'PENDING_REVIEW') return 'Pending';
  if (value === 'REJECTED') return 'Rejected';
  if (value === 'EXPIRED' || value === 'EXPIREE') return 'Expired';
  if (value === 'ARCHIVED' || value === 'ARCHIVEE') return 'Archived';
  return status || 'Unknown';
};

export const originLabel = (opportunity) => (
  opportunity?.published_by === 'organization' ? 'Organization' : 'Scraper'
);

export const originClassName = (opportunity) => (
  opportunity?.published_by === 'organization'
    ? 'border-violet-200 bg-violet-50 text-violet-700'
    : sourceClassName(opportunity?.source)
);
