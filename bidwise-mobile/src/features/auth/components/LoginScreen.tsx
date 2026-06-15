import { useState, useEffect, useRef } from 'react';
import {
  Animated,
  Easing,
  Image,
  ScrollView,
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

const bidwiseLogo = require('@/assets/images/bidwise-logo-web.png');
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PRODUCT_BENEFITS = [
  'Multi-source collection',
  'AI recommendations',
  'Application assistance',
  'Smart tracking',
];

export default function LoginScreen() {
  const router = useRouter();
  const { loginWithGoogle } = useAuth();
  const { promptGoogle, idToken, googleLoading, googleError } = useGoogleAuth();
  const { isDark, toggleColorScheme } = useThemeMode();
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [googleSending, setGoogleSending] = useState(false);
  const [error, setError] = useState('');
  const topGlowProgress = useRef(new Animated.Value(0)).current;
  const bottomGlowProgress = useRef(new Animated.Value(0)).current;

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const borderColor = useThemeColor({}, 'border');
  const cardColor = useThemeColor({}, 'card');
  const iconColor = useThemeColor({}, 'icon');

  const handleRequestOTP = async () => {
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail) {
      setError('Email is required.');
      return;
    }

    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setError('Please enter a valid email address.');
      return;
    }

    setSending(true);
    setError('');
    try {
      const response = await requestOTP(normalizedEmail);
      router.push({
        pathname: '/otp',
        params: {
          email: normalizedEmail,
          delivery: String(response?.message || ''),
        },
      });
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
        ?? (e.code === 'ERR_NETWORK'
          ? 'Network error: cannot reach the server.'
          : 'We could not send a login code right now. Please try again.');
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
        router.replace((!onboarding_completed || is_new_user) ? '/onboarding' : '/explore');
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

  useEffect(() => {
    const createGlowLoop = (value: Animated.Value, duration: number, delay = 0) => Animated.loop(
      Animated.sequence([
        Animated.delay(delay),
        Animated.timing(value, {
          toValue: 1,
          duration,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(value, {
          toValue: 0,
          duration,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ]),
    );

    const topLoop = createGlowLoop(topGlowProgress, 9000);
    const bottomLoop = createGlowLoop(bottomGlowProgress, 11000, 1200);
    topLoop.start();
    bottomLoop.start();

    return () => {
      topLoop.stop();
      bottomLoop.stop();
    };
  }, [bottomGlowProgress, topGlowProgress]);

  const topGlowTransform = {
    transform: [
      {
        translateX: topGlowProgress.interpolate({
          inputRange: [0, 1],
          outputRange: [0, -24],
        }),
      },
      {
        translateY: topGlowProgress.interpolate({
          inputRange: [0, 1],
          outputRange: [0, 18],
        }),
      },
      {
        scale: topGlowProgress.interpolate({
          inputRange: [0, 1],
          outputRange: [1, 1.08],
        }),
      },
    ],
  };

  const bottomGlowTransform = {
    transform: [
      {
        translateX: bottomGlowProgress.interpolate({
          inputRange: [0, 1],
          outputRange: [0, 28],
        }),
      },
      {
        translateY: bottomGlowProgress.interpolate({
          inputRange: [0, 1],
          outputRange: [0, -18],
        }),
      },
      {
        scale: bottomGlowProgress.interpolate({
          inputRange: [0, 1],
          outputRange: [1, 1.06],
        }),
      },
    ],
  };

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View pointerEvents="none" style={styles.backgroundDecor}>
        <Animated.View
          style={[
            styles.topGlow,
            { backgroundColor: isDark ? '#1e3a5f' : '#dbeafe' },
            topGlowTransform,
          ]}
        />
        <Animated.View
          style={[
            styles.bottomGlow,
            { backgroundColor: isDark ? '#172554' : '#e0e7ff' },
            bottomGlowTransform,
          ]}
        />
      </View>

      <TouchableOpacity
        style={[styles.themeToggle, { backgroundColor: cardColor, borderColor }]}
        onPress={toggleColorScheme}
        activeOpacity={0.8}
        accessibilityRole="button"
        accessibilityLabel={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        <Ionicons name={isDark ? 'sunny-outline' : 'moon-outline'} size={20} color={iconColor} />
      </TouchableOpacity>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          <View style={styles.brand}>
            <Image source={bidwiseLogo} style={styles.logoImage} resizeMode="contain" />
            <Text style={[styles.eyebrow, { color: tintColor }]}>MULTIPLE SOURCES. ONE PLATFORM.</Text>
            <Text style={[styles.title, { color: textColor }]}>
              Stop searching everywhere.{'\n'}
              <Text style={{ color: tintColor }}>Find what matters here.</Text>
            </Text>

          </View>

          <View style={styles.benefitsGrid}>
            {PRODUCT_BENEFITS.map((benefit) => (
              <View key={benefit} style={styles.benefitItem}>
                <Ionicons name="checkmark-circle-outline" size={20} color={tintColor} />
                <Text style={[styles.benefitLabel, { color: textColor }]}>{benefit}</Text>
              </View>
            ))}
          </View>

          <View style={styles.authPanel}>
            <TouchableOpacity
              style={[styles.googleButton, { backgroundColor: cardColor, borderColor, opacity: googleLoading || googleSending ? 0.5 : 1 }]}
              onPress={handleGoogleLogin}
              activeOpacity={0.7}
              disabled={googleLoading || googleSending}
              accessibilityRole="button"
              accessibilityLabel="Continue with Google"
            >
              {googleSending ? (
                <ActivityIndicator color={textColor} />
              ) : (
                <View style={styles.buttonContent}>
                  <Ionicons name="logo-google" size={19} color={textColor} />
                  <Text style={[styles.googleButtonText, { color: textColor }]}>Continue with Google</Text>
                </View>
              )}
            </TouchableOpacity>

            <View style={styles.separator}>
              <View style={[styles.separatorLine, { backgroundColor: borderColor }]} />
              <Text style={[styles.separatorText, { color: mutedColor }]}>or</Text>
              <View style={[styles.separatorLine, { backgroundColor: borderColor }]} />
            </View>

            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            <View style={[styles.inputShell, { borderColor, backgroundColor }]}>
              <Ionicons name="mail-outline" size={19} color={mutedColor} />
              <TextInput
                style={[styles.input, { color: textColor }]}
                placeholder="Email address"
                placeholderTextColor={mutedColor}
                value={email}
                onChangeText={(value) => { setEmail(value); setError(''); }}
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
                editable={!sending}
                accessibilityLabel="Email address"
              />
            </View>

            <TouchableOpacity
              style={[styles.primaryButton, { backgroundColor: tintColor, opacity: email.trim() && !sending ? 1 : 0.5 }]}
              onPress={handleRequestOTP}
              activeOpacity={0.8}
              disabled={!email.trim() || sending}
              accessibilityRole="button"
              accessibilityLabel="Send secure login code"
            >
              {sending ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <View style={styles.buttonContent}>
                  <Text style={styles.primaryButtonText}>Send secure login code</Text>
                  <Ionicons name="arrow-forward" size={18} color="#ffffff" />
                </View>
              )}
            </TouchableOpacity>

            <Text style={[styles.securityText, { color: mutedColor }]}>Password-free and secure</Text>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  backgroundDecor: {
    ...StyleSheet.absoluteFillObject,
    overflow: 'hidden',
  },
  topGlow: {
    position: 'absolute',
    width: 280,
    height: 280,
    borderRadius: 140,
    top: -150,
    right: -100,
    opacity: 0.6,
  },
  bottomGlow: {
    position: 'absolute',
    width: 240,
    height: 240,
    borderRadius: 120,
    bottom: -140,
    left: -100,
    opacity: 0.45,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingVertical: 36,
  },
  content: {
    width: '100%',
    maxWidth: 520,
    alignSelf: 'center',
    paddingHorizontal: 22,
  },
  themeToggle: {
    position: 'absolute',
    top: 50,
    right: 20,
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
    marginBottom: 18,
  },
  logoImage: {
    width: 130,
    height: 70,
    marginBottom: 12,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.4,
    marginBottom: 8,
  },
  title: {
    fontSize: 29,
    lineHeight: 35,
    fontWeight: '900',
    marginBottom: 9,
    letterSpacing: 0,
    textAlign: 'center',
  },
  subtitle: {
    maxWidth: 380,
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 21,
  },
  benefitsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -4,
    marginBottom: 22,
  },
  benefitItem: {
    width: '50%',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 4,
    marginBottom: 12,
    gap: 7,
  },
  benefitLabel: {
    flex: 1,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '600',
  },
  authPanel: {
    width: '100%',
  },
  googleButton: {
    borderWidth: 1,
    borderRadius: 10,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  googleButtonText: {
    fontSize: 15,
    fontWeight: '600',
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 9,
  },
  separator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 17,
  },
  separatorLine: {
    flex: 1,
    height: 1,
  },
  separatorText: {
    marginHorizontal: 12,
    fontSize: 12,
  },
  inputShell: {
    minHeight: 50,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    marginBottom: 12,
  },
  input: {
    flex: 1,
    paddingHorizontal: 10,
    paddingVertical: 13,
    fontSize: 16,
  },
  errorText: {
    color: '#dc2626',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
  primaryButton: {
    minHeight: 50,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  securityText: {
    marginTop: 12,
    fontSize: 12,
    textAlign: 'center',
  },
});
