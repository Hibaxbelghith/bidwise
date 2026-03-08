import { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';

import { useThemeColor } from '@/hooks/use-theme-color';
import { requestOTP } from '@/src/services/auth';
import { useAuth } from '@/src/context/AuthContext';
import { useGoogleAuth } from '@/src/hooks/useGoogleAuth';

export default function LoginScreen() {
  const router = useRouter();
  const { loginWithGoogle } = useAuth();
  const { promptGoogle, idToken, googleLoading, googleError } = useGoogleAuth();
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [googleSending, setGoogleSending] = useState(false);
  const [error, setError] = useState('');

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');

  const handleRequestOTP = async () => {
    if (!email.trim()) return;
    setSending(true);
    setError('');
    try {
      await requestOTP(email.trim());
      router.push({ pathname: '/otp', params: { email: email.trim() } });
    } catch (e: any) {
      console.error('[OTP Request Error]', {
        message: e.message,
        status: e.response?.status,
        data: e.response?.data,
        url: e.config?.url,
        baseURL: e.config?.baseURL,
      });
      const msg = e.response?.data?.error
        ?? e.response?.data?.detail
        ?? (e.code === 'ERR_NETWORK' ? `Network error: cannot reach server` : `Error: ${e.message}`);
      setError(msg);
    } finally {
      setSending(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    await promptGoogle();
  };

  // When Google returns an id_token, send it to the backend
  useEffect(() => {
    if (!idToken) return;
    (async () => {
      setGoogleSending(true);
      setError('');
      try {
        const { is_new_user, onboarding_completed } = await loginWithGoogle(idToken);
        router.replace((!onboarding_completed || is_new_user) ? '/onboarding' : '/dashboard');
      } catch (e: any) {
        const msg = e.response?.data?.error
          ?? (e.code === 'ERR_NETWORK' ? `Network error: cannot reach server` : `Error: ${e.message}`);
        setError(msg);
      } finally {
        setGoogleSending(false);
      }
    })();
  }, [idToken]);

  // Show google auth errors
  useEffect(() => {
    if (googleError) setError(googleError);
  }, [googleError]);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        {/* Brand */}
        <View style={styles.brand}>
          <View style={[styles.logoBox, { backgroundColor: tintColor }]}>
            <Text style={styles.logoText}>B</Text>
          </View>
          <Text style={[styles.title, { color: textColor }]}>BidWise</Text>
          <Text style={[styles.subtitle, { color: mutedColor }]}>
            Sign in to find your next opportunity
          </Text>
        </View>

        {/* Google Button */}
        <TouchableOpacity
          style={[styles.googleButton, { borderColor: useThemeColor({}, 'border'), opacity: googleLoading || googleSending ? 0.5 : 1 }]}
          onPress={handleGoogleLogin}
          activeOpacity={0.7}
          disabled={googleLoading || googleSending}
        >
          {googleSending ? (
            <ActivityIndicator color={textColor} />
          ) : (
            <Text style={[styles.googleButtonText, { color: textColor }]}>
              Continue with Google
            </Text>
          )}
        </TouchableOpacity>

        {/* Separator */}
        <View style={styles.separator}>
          <View style={[styles.separatorLine, { backgroundColor: useThemeColor({}, 'border') }]} />
          <Text style={[styles.separatorText, { color: mutedColor }]}>or</Text>
          <View style={[styles.separatorLine, { backgroundColor: useThemeColor({}, 'border') }]} />
        </View>

        {/* Error */}
        {error ? (
          <Text style={[styles.errorText, { color: '#ef4444' }]}>{error}</Text>
        ) : null}

        {/* Email Input */}
        <TextInput
          style={[
            styles.input,
            {
              color: textColor,
              borderColor: useThemeColor({}, 'border'),
              backgroundColor: useThemeColor({}, 'card'),
            },
          ]}
          placeholder="Enter your email"
          placeholderTextColor={mutedColor}
          value={email}
          onChangeText={(t) => { setEmail(t); setError(''); }}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
          editable={!sending}
        />

        {/* Send Code Button */}
        <TouchableOpacity
          style={[styles.primaryButton, { backgroundColor: tintColor, opacity: email.trim() && !sending ? 1 : 0.5 }]}
          onPress={handleRequestOTP}
          activeOpacity={0.8}
          disabled={!email.trim() || sending}
        >
          {sending ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.primaryButtonText}>Send login code</Text>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  brand: {
    alignItems: 'center',
    marginBottom: 48,
  },
  logoBox: {
    width: 56,
    height: 56,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  logoText: {
    color: '#ffffff',
    fontSize: 28,
    fontWeight: '700',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 22,
  },
  googleButton: {
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 24,
  },
  googleButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  separator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  separatorLine: {
    flex: 1,
    height: 1,
  },
  separatorText: {
    marginHorizontal: 16,
    fontSize: 14,
  },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    marginBottom: 16,
  },
  errorText: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
  primaryButton: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});
