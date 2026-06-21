export type MobileApplicationStatusMeta = {
  label: string;
  datePrefix: string;
  tone: 'blue' | 'green' | 'red' | 'amber' | 'neutral';
};

const META: Record<string, MobileApplicationStatusMeta> = {
  SUBMITTED: {
    label: 'Application submitted',
    datePrefix: 'Applied',
    tone: 'blue',
  },
  VIEWED_BY_ORGANIZATION: {
    label: 'Under review',
    datePrefix: 'Applied',
    tone: 'blue',
  },
  SHORTLISTED: {
    label: 'Under review',
    datePrefix: 'Applied',
    tone: 'blue',
  },
  REJECTED: {
    label: 'Under review',
    datePrefix: 'Applied',
    tone: 'blue',
  },
  WITHDRAWN: {
    label: 'Withdrawn by you',
    datePrefix: 'Withdrawn',
    tone: 'neutral',
  },
  EXTERNAL_CLICKED: {
    label: 'External application started',
    datePrefix: 'Opened',
    tone: 'amber',
  },
  EXTERNAL_APPLIED_CONFIRMED: {
    label: 'Applied externally',
    datePrefix: 'Confirmed',
    tone: 'green',
  },
  EXTERNAL_REMIND_LATER: {
    label: 'Saved for later',
    datePrefix: 'Saved',
    tone: 'neutral',
  },
};

export function getMobileApplicationStatusMeta(status?: string | null): MobileApplicationStatusMeta {
  const key = String(status || '').trim().toUpperCase();
  return (
    META[key] || {
      label: 'Updated',
      datePrefix: 'Updated',
      tone: 'neutral',
    }
  );
}

export function canWithdrawApplication(status?: string | null): boolean {
  const key = String(status || '').trim().toUpperCase();
  return ['SUBMITTED', 'VIEWED_BY_ORGANIZATION'].includes(key);
}
