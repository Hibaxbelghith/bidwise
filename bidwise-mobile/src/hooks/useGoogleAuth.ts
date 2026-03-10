import { useCallback, useState } from 'react';
import { NativeModules } from 'react-native';

const googleAvailable = !!NativeModules.RNGoogleSignin;

// Web client ID — the native SDK uses it to request an id_token
const WEB_CLIENT_ID =
  '149784459020-aknnq7m4rlur7pj32cd1elkf68cpbblt.apps.googleusercontent.com';

function getGoogleModule() {
  // Only require when we know the native module exists
  const mod = require('@react-native-google-signin/google-signin');
  return mod;
}

if (googleAvailable) {
  const { GoogleSignin } = getGoogleModule();
  GoogleSignin.configure({ webClientId: WEB_CLIENT_ID });
}

export function useGoogleAuth() {
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const promptGoogle = useCallback(async () => {
    if (!googleAvailable) {
      setError('Google Sign-In is not available in Expo Go. Use a development build.');
      return;
    }
    try {
      setLoading(true);
      setError(null);

      const { GoogleSignin, isSuccessResponse, isErrorWithCode, statusCodes } = getGoogleModule();

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
      const { isErrorWithCode, statusCodes } = getGoogleModule();
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
  }, []);

  return {
    promptGoogle,
    idToken,
    googleLoading: loading,
    googleError: error,
  };
}
