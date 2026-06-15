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
  const { email, delivery } = useLocalSearchParams<{ email: string; delivery?: string }>();
  const router = useRouter();
  const { loginWithOTP } = useAuth();
  const [code, setCode] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');
  const [resending, setResending] = useState(false);
  const [deliveryHint, setDeliveryHint] = useState(String(delivery || ''));
  const inputRef = useRef<TextInput>(null);

  const backgroundColor = useThemeColor({}, 'background');
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const borderColor = useThemeColor({}, 'border');

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
      router.replace((!onboarding_completed || is_new_user) ? '/onboarding' : '/explore');
    } catch (e: any) {
      const msg = e.response?.data?.error ?? e.response?.data?.detail ?? 'Invalid code. Please try again.';
      setError(msg);
      setCode('');
    } finally {
      setVerifying(false);
    }
  }, [code, email, loginWithOTP, router]);

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
      const response = await requestOTP(email);
      setDeliveryHint(String(response?.message || ''));
    } catch {
      setError('Could not resend code. Try again.');
    } finally {
      setResending(false);
    }
  };

  const digits = Array.from({ length: CODE_LENGTH }, (_, i) => code[i] || '');
  const normalizedDelivery = deliveryHint.toLowerCase();
  const otpHelpText = normalizedDelivery.includes('simulated')
    ? 'Development mode: your mobile login code is available in backend logs.'
    : 'Enter the 6-digit code sent for this email address.';

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <Text style={[styles.backText, { color: tintColor }]}>Back</Text>
        </TouchableOpacity>

        <Text style={[styles.title, { color: textColor }]}>Enter your login code</Text>
        <Text style={[styles.subtitle, { color: mutedColor }]}>
          Use the 6-digit code for{'\n'}
          <Text style={{ fontWeight: '600', color: textColor }}>{email}</Text>
        </Text>
        <Text style={[styles.helperText, { color: mutedColor }]}>{otpHelpText}</Text>

        {error ? (
          <Text
            style={[styles.errorText, { color: '#ef4444' }]}
            accessibilityRole="alert"
            accessibilityLiveRegion="assertive"
          >
            {error}
          </Text>
        ) : null}

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
          accessibilityHint="Enter the 6-digit code for your BidWise login"
        />

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
              accessibilityLabel={
                digit
                  ? `Digit ${index + 1} of ${CODE_LENGTH}: ${digit}`
                  : `Digit ${index + 1} of ${CODE_LENGTH}: empty`
              }
            >
              <Text style={[styles.digitText, { color: textColor }]}>{digit}</Text>
            </View>
          ))}
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.primaryButton,
            { backgroundColor: tintColor, opacity: code.length === CODE_LENGTH && !verifying ? 1 : 0.5 },
          ]}
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
    marginBottom: 10,
  },
  helperText: {
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 22,
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
