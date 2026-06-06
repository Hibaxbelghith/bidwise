import { useEffect, useRef, useState } from 'react';

const TURNSTILE_SCRIPT_ID = 'cloudflare-turnstile-script';
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '';

export const isTurnstileEnabled = () => Boolean(TURNSTILE_SITE_KEY);

const ensureTurnstileScript = () =>
  new Promise((resolve, reject) => {
    if (window.turnstile) {
      resolve(window.turnstile);
      return;
    }

    const existing = document.getElementById(TURNSTILE_SCRIPT_ID);
    if (existing) {
      existing.addEventListener('load', () => resolve(window.turnstile), { once: true });
      existing.addEventListener('error', reject, { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = TURNSTILE_SCRIPT_ID;
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve(window.turnstile);
    script.onerror = reject;
    document.head.appendChild(script);
  });

const TurnstileChallenge = ({ onVerify, onExpire, resetSignal = 0 }) => {
  const containerRef = useRef(null);
  const widgetIdRef = useRef(null);
  const onVerifyRef = useRef(onVerify);
  const onExpireRef = useRef(onExpire);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    onVerifyRef.current = onVerify;
    onExpireRef.current = onExpire;
  }, [onExpire, onVerify]);

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY || !containerRef.current) return undefined;

    let isMounted = true;
    setLoadError('');

    ensureTurnstileScript()
      .then((turnstile) => {
        if (!isMounted || !containerRef.current) return;
        if (widgetIdRef.current !== null) {
          turnstile.remove(widgetIdRef.current);
          widgetIdRef.current = null;
        }
        widgetIdRef.current = turnstile.render(containerRef.current, {
          sitekey: TURNSTILE_SITE_KEY,
          callback: (token) => onVerifyRef.current?.(token),
          'expired-callback': () => {
            onExpireRef.current?.();
          },
          'error-callback': () => {
            onExpireRef.current?.();
          },
        });
      })
      .catch(() => {
        if (isMounted) {
          setLoadError('Anti-bot check could not load. Please refresh and try again.');
          onExpireRef.current?.();
        }
      });

    return () => {
      isMounted = false;
      if (widgetIdRef.current !== null && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [resetSignal]);

  if (!TURNSTILE_SITE_KEY) {
    return null;
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3">
      <p className="mb-3 text-sm font-semibold text-neutral-900">Anti-bot verification</p>
      <div ref={containerRef} />
      {loadError ? <p className="mt-2 text-sm text-red-600">{loadError}</p> : null}
    </div>
  );
};

export default TurnstileChallenge;
