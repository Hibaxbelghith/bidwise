import { useState, useEffect } from 'react';
import {
  Image,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { useGoogleAuth } from '@/src/features/auth/hooks/useGoogleAuth';
import { requestOTP } from '@/src/features/auth/services/authService';
import { useThemeMode } from '@/src/shared/context/ThemeModeContext';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

const bidwiseLogo = require('@/assets/images/favicon.png');

export default function LoginScreen() {
  const router = useRouter();
  const { loginWithGoogle } = useAuth();
  const { promptGoogle, idToken, googleLoading, googleError } = useGoogleAuth();
  const { isDark, toggleColorScheme } = useThemeMode();
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [googleSending, setGoogleSending] = useState(false);
  const [error, setError] = useState('');

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const borderColor = useThemeColor({}, 'border');
  const cardColor = useThemeColor({}, 'card');
  const iconColor = useThemeColor({}, 'icon');

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
        router.replace((!onboarding_completed || is_new_user) ? '/onboarding' : '/for-you');
      } catch (e: any) {
        const msg = e.response?.data?.error
          ?? (e.code === 'ERR_NETWORK' ? `Network error: cannot reach server` : `Error: ${e.message}`);
        setError(msg);
      } finally {
        setGoogleSending(false);
      }
    })();
  }, [idToken, loginWithGoogle, router]);

  // Show google auth errors
  useEffect(() => {
    if (googleError) setError(googleError);
  }, [googleError]);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <TouchableOpacity
        style={[styles.themeToggle, { backgroundColor: cardColor, borderColor }]}
        onPress={toggleColorScheme}
        activeOpacity={0.8}
        accessibilityRole="button"
        accessibilityLabel={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        <Ionicons name={isDark ? 'sunny-outline' : 'moon-outline'} size={20} color={iconColor} />
      </TouchableOpacity>

      <View style={styles.content}>
        {/* Brand */}
        <View style={styles.brand}>
          <View style={[styles.logoBox, { backgroundColor: cardColor, borderColor }]}>
            <Image source={bidwiseLogo} style={styles.logoImage} resizeMode="contain" />
          </View>
          <Text style={[styles.title, { color: textColor }]}>BidWise</Text>
          <Text style={[styles.subtitle, { color: mutedColor }]}>
            Sign in to find your next opportunity
          </Text>
        </View>

        {/* Google Button */}
        <TouchableOpacity
          style={[styles.googleButton, { backgroundColor: cardColor, borderColor, opacity: googleLoading || googleSending ? 0.5 : 1 }]}
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
          <View style={[styles.separatorLine, { backgroundColor: borderColor }]} />
          <Text style={[styles.separatorText, { color: mutedColor }]}>or</Text>
          <View style={[styles.separatorLine, { backgroundColor: borderColor }]} />
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
              borderColor,
              backgroundColor: cardColor,
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
  themeToggle: {
    position: 'absolute',
    top: 56,
    right: 24,
    zIndex: 10,
    width: 44,
    height: 44,
    borderWidth: 1,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brand: {
    alignItems: 'center',
    marginBottom: 48,
  },
  logoBox: {
    width: 72,
    height: 72,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.08,
    shadowRadius: 20,
    elevation: 3,
  },
  logoImage: {
    width: 52,
    height: 52,
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
