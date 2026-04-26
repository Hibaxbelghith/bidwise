import { useCallback, useEffect, useMemo, useState } from 'react';
import { NativeModules } from 'react-native';

type GoogleSigninModule = typeof import('@react-native-google-signin/google-signin');

// Web client ID — the native SDK uses it to request an id_token
const WEB_CLIENT_ID =
  '149784459020-aknnq7m4rlur7pj32cd1elkf68cpbblt.apps.googleusercontent.com';

function hasNativeGoogleModule(): boolean {
  const nativeModules = NativeModules as Record<string, unknown>;
  return Boolean(nativeModules.RNGoogleSignin || nativeModules.RNGoogleSigninn);
}

function getGoogleModule(): GoogleSigninModule | null {
  if (!hasNativeGoogleModule()) {
    return null;
  }

  // This must stay lazy to avoid crashing Expo Go when the native module is absent.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  return require('@react-native-google-signin/google-signin') as GoogleSigninModule;
}

export function useGoogleAuth() {
  const googleModule = useMemo(() => getGoogleModule(), []);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!googleModule) return;
    googleModule.GoogleSignin.configure({ webClientId: WEB_CLIENT_ID });
  }, [googleModule]);

  const promptGoogle = useCallback(async () => {
    if (!googleModule) {
      setError('Google Sign-In is not available in Expo Go. Use a development build.');
      return;
    }

    const { GoogleSignin, isErrorWithCode, isSuccessResponse, statusCodes } = googleModule;

    try {
      setLoading(true);
      setError(null);

      await GoogleSignin.hasPlayServices();
      // Sign out first to always show account picker
      await GoogleSignin.signOut();
      const response = await GoogleSignin.signIn();

      if (isSuccessResponse(response)) {
        const token = response.data?.idToken ?? null;
        if (!token) {
          setError('Google returned no id_token. Check webClientId config.');
          return;
        }
        setIdToken(token);
      } else {
        setError('Google sign-in was cancelled');
      }
    } catch (e: any) {
      if (isErrorWithCode(e)) {
        switch (e.code) {
          case statusCodes.SIGN_IN_CANCELLED:
            setError(null); // user cancelled, not an error
            break;
          case statusCodes.PLAY_SERVICES_NOT_AVAILABLE:
            setError('Google Play Services not available');
            break;
          default:
            setError(e.message ?? 'Google sign-in failed');
        }
      } else {
        setError(e.message ?? 'Google sign-in failed');
      }
    } finally {
      setLoading(false);
    }
  }, [googleModule]);

  return {
    promptGoogle,
    idToken,
    googleLoading: loading,
    googleError: error,
  };
}
