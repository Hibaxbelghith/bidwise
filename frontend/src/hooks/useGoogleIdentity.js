import { useEffect, useRef, useState, useCallback } from 'react';

const GIS_SCRIPT_URL = 'https://accounts.google.com/gsi/client';


/**
 * Dynamically loads Google Identity Services and renders the
 * "Continue with Google" button into the given container ref.
 *
 * Safety guarantees:
 * - Script is loaded only once (dedup via ref).
 * - google.accounts.id.initialize() is called only once (ref guard).
 * - If VITE_GOOGLE_CLIENT_ID is missing/empty, nothing loads and
 *   `ready` stays false → caller hides the button.
 * - google.accounts.id.prompt() is NOT called.
 * - Missing response.credential is treated as an error.
 *
 * @param {Function} onSuccess - Called with the id_token string on success.
 * @param {Function} onError   - Called with an error message string on failure.
 * @returns {{ containerRef: React.RefObject, ready: boolean }}
 */
export function useGoogleIdentity(onSuccess, onError) {
	const initializedRef = useRef(false);
	const scriptLoadedRef = useRef(false);
	const [ready, setReady] = useState(false);

	const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

	// Stable callback ref so GIS always calls the latest version
	const onSuccessRef = useRef(onSuccess);
	const onErrorRef = useRef(onError);
	useEffect(() => {
		onSuccessRef.current = onSuccess;
		onErrorRef.current = onError;
	}, [onSuccess, onError]);

	const handleCredentialResponse = useCallback((response) => {
		if (!response?.credential) {
			onErrorRef.current?.('Google authentication failed — no credential received.');
			return;
		}
		onSuccessRef.current?.(response.credential);
	}, []);

	// Callback ref: fires every time the DOM node is attached (including
	// re-mounts when switching from OTP step back to email step).
	// Calls renderButton on each fresh node so the Google button always appears.
	const containerRef = useCallback(
		(node) => {
			if (!node || !ready || !window.google?.accounts?.id) return;

			window.google.accounts.id.renderButton(node, {
				type: 'standard',
				theme: 'outline',
				size: 'large',
				text: 'continue_with',
				width: '100%',
				logo_alignment: 'left',
			});
		},
		[ready],
	);

	// Load GIS script + call initialize() (no DOM needed)
	useEffect(() => {
		// Guard: no client ID → stay hidden
		if (!clientId) return;

		// Guard: already initialized in this component lifecycle
		if (initializedRef.current) return;

		const initializeGIS = () => {
			if (initializedRef.current) return;
			initializedRef.current = true;

			try {
				window.google.accounts.id.initialize({
					client_id: clientId,
					callback: handleCredentialResponse,
					auto_select: false,
					cancel_on_tap_outside: true,
				});

				// Signal that GIS is initialized — the callback ref will
				// render the button on the next commit.
				setReady(true);
			} catch {
				onErrorRef.current?.('Failed to initialize Google Sign-In.');
			}
		};

		// If script is already on the page (e.g. HMR re-mount)
		if (window.google?.accounts?.id) {
			initializeGIS();
			return;
		}

		// Prevent duplicate script tags across fast re-renders
		if (scriptLoadedRef.current) return;
		scriptLoadedRef.current = true;

		const script = document.createElement('script');
		script.src = GIS_SCRIPT_URL;
		script.async = true;
		script.defer = true;

		script.onload = initializeGIS;
		script.onerror = () => {
			scriptLoadedRef.current = false;
			onErrorRef.current?.('Failed to load Google Sign-In script.');
		};

		document.head.appendChild(script);

		// No cleanup removal — GIS expects the script to persist.
		// The initializedRef guard prevents double-init on HMR.
	}, [clientId, handleCredentialResponse]);

	return { containerRef, ready };
}
