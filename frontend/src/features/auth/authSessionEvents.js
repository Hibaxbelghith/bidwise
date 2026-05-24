export const AUTH_REDIRECT_EVENT = 'bidwise:auth-redirect';
export const AUTH_NOTICE_STORAGE_KEY = 'bidwise:auth-notice';

export const AUTH_NOTICE_MESSAGES = {
  session_expired: 'Your session expired. Sign in again to keep working.',
};

export const storeAuthNotice = (reason = 'session_expired') => {
  if (typeof window === 'undefined') return;

  const message = AUTH_NOTICE_MESSAGES[reason] || AUTH_NOTICE_MESSAGES.session_expired;
  try {
    window.sessionStorage.setItem(
      AUTH_NOTICE_STORAGE_KEY,
      JSON.stringify({
        reason,
        message,
        createdAt: Date.now(),
      }),
    );
  } catch {
    // Ignore storage errors.
  }
};

export const consumeAuthNotice = () => {
  if (typeof window === 'undefined') return null;

  try {
    const raw = window.sessionStorage.getItem(AUTH_NOTICE_STORAGE_KEY);
    if (!raw) return null;
    window.sessionStorage.removeItem(AUTH_NOTICE_STORAGE_KEY);
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

export const dispatchAuthRedirect = ({
  redirectPath = '/login',
  reason = 'session_expired',
} = {}) => {
  if (typeof window === 'undefined') return;

  storeAuthNotice(reason);
  window.dispatchEvent(
    new CustomEvent(AUTH_REDIRECT_EVENT, {
      detail: { redirectPath, reason },
    }),
  );
};
