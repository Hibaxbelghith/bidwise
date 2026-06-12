import { useState, useRef, useEffect, useCallback } from 'react';
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
import { useLocalSearchParams, useRouter } from 'expo-router';

import { useAuth } from '@/src/features/auth/context/AuthContext';
import { requestOTP } from '@/src/features/auth/services/authService';
import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

const CODE_LENGTH = 6;

export default function OTPScreen() {
  const { email } = useLocalSearchParams<{ email: string }>();
  const router = useRouter();
  const { loginWithOTP } = useAuth();
  const [code, setCode] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');
  const [resending, setResending] = useState(false);
  const inputRef = useRef<TextInput>(null);

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const borderColor = useThemeColor({}, 'border');

  // Auto-focus on mount
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 300);
    return () => clearTimeout(timer);
  }, []);

  const handleCodeChange = (text: string) => {
    const cleaned = text.replace(/[^0-9]/g, '').slice(0, CODE_LENGTH);
    setCode(cleaned);
    setError('');
  };

  const handleVerify = useCallback(async () => {
    if (code.length !== CODE_LENGTH || !email) return;
    setVerifying(true);
    setError('');
    try {
      const { is_new_user, onboarding_completed } = await loginWithOTP(email, code);
      router.replace((!onboarding_completed || is_new_user) ? '/onboarding' : '/for-you');
    } catch (e: any) {
      const msg = e.response?.data?.error ?? e.response?.data?.detail ?? 'Invalid code. Please try again.';
      setError(msg);
      setCode('');
    } finally {
      setVerifying(false);
    }
  }, [code, email, loginWithOTP, router]);

  // Auto-submit when 6 digits are entered (e.g. from paste or autofill)
  useEffect(() => {
    if (code.length === CODE_LENGTH && !verifying) {
      void handleVerify();
    }
  }, [code, handleVerify, verifying]);

  const handleResend = async () => {
    if (!email || resending) return;
    setResending(true);
    setError('');
    try {
      await requestOTP(email);
    } catch {
      setError('Could not resend code. Try again.');
    } finally {
      setResending(false);
    }
  };

  // Render individual digit boxes
  const digits = Array.from({ length: CODE_LENGTH }, (_, i) => code[i] || '');

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <Text style={[styles.backText, { color: tintColor }]}>← Back</Text>
        </TouchableOpacity>

        <Text style={[styles.title, { color: textColor }]}>Check your email</Text>
        <Text style={[styles.subtitle, { color: mutedColor }]}>
          We sent a 6-digit code to{'\n'}
          <Text style={{ fontWeight: '600', color: textColor }}>{email}</Text>
        </Text>

        {/* Error */}
        {error ? (
          <Text
            style={[styles.errorText, { color: '#ef4444' }]}
            accessibilityRole="alert"
            accessibilityLiveRegion="assertive"
          >
            {error}
          </Text>
        ) : null}

        {/* Hidden input — OTP autofill enabled */}
        <TextInput
          ref={inputRef}
          style={styles.hiddenInput}
          value={code}
          onChangeText={handleCodeChange}
          keyboardType="number-pad"
          maxLength={CODE_LENGTH}
          autoFocus
          editable={!verifying}
          textContentType="oneTimeCode"
          autoComplete="sms-otp"
          importantForAutofill="yes"
          accessibilityLabel="6-digit verification code"
          accessibilityHint="Enter the 6-digit code sent to your email"
        />

        {/* Visual digit boxes */}
        <TouchableOpacity
          style={styles.codeRow}
          activeOpacity={1}
          onPress={() => inputRef.current?.focus()}
          accessible={false}
        >
          {digits.map((digit, index) => (
            <View
              key={index}
              style={[
                styles.digitBox,
                {
                  borderColor: index === code.length ? tintColor : borderColor,
                  borderWidth: index === code.length ? 2 : 1,
                },
              ]}
              accessibilityLabel={digit ? `Digit ${index + 1} of ${CODE_LENGTH}: ${digit}` : `Digit ${index + 1} of ${CODE_LENGTH}: empty`}
            >
              <Text style={[styles.digitText, { color: textColor }]}>{digit}</Text>
            </View>
          ))}
        </TouchableOpacity>

        {/* Verify button */}
        <TouchableOpacity
          style={[styles.primaryButton, { backgroundColor: tintColor, opacity: code.length === CODE_LENGTH && !verifying ? 1 : 0.5 }]}
          onPress={handleVerify}
          activeOpacity={0.8}
          disabled={code.length !== CODE_LENGTH || verifying}
        >
          {verifying ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.primaryButtonText}>Verify</Text>
          )}
        </TouchableOpacity>

        {/* Resend */}
        <TouchableOpacity style={styles.resendButton} onPress={handleResend} disabled={resending}>
          <Text style={[styles.resendText, { color: mutedColor }]}>
            {resending ? 'Sending...' : "Didn't receive the code? "}
            {!resending && <Text style={{ color: tintColor, fontWeight: '600' }}>Resend</Text>}
          </Text>
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
  backButton: {
    position: 'absolute',
    top: 60,
    left: 32,
  },
  backText: {
    fontSize: 16,
    fontWeight: '600',
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 32,
  },
  errorText: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
  hiddenInput: {
    position: 'absolute',
    opacity: 0,
  },
  codeRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 10,
    marginBottom: 32,
  },
  digitBox: {
    width: 48,
    height: 56,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  digitText: {
    fontSize: 24,
    fontWeight: '700',
  },
  primaryButton: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 24,
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  resendButton: {
    alignItems: 'center',
  },
  resendText: {
    fontSize: 14,
  },
});
