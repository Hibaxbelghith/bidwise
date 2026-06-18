import { type ReactNode } from 'react';
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

type ProfileEditorPageProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
  loading: boolean;
  onRefresh: () => Promise<void>;
  onSave: () => Promise<boolean>;
  saving: boolean;
  isDirty: boolean;
  formError?: string;
  successMessage?: string;
  saveLabel?: string;
  showSaveBar?: boolean;
};

export default function ProfileEditorPage({
  title,
  subtitle,
  children,
  loading,
  onRefresh,
  onSave,
  saving,
  isDirty,
  formError,
  successMessage,
  saveLabel = 'Save changes',
  showSaveBar = true,
}: ProfileEditorPageProps) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const cardColor = useThemeColor({}, 'card');
  const borderColor = useThemeColor({}, 'border');
  const backgroundColor = useThemeColor({}, 'background');
  const hasFeedback = Boolean(formError || successMessage);

  return (
    <View style={[styles.root, { backgroundColor }]}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingBottom: 126 + Math.max(insets.bottom, 12) },
        ]}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={onRefresh}
            tintColor={tintColor}
            colors={[tintColor]}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.headerBlock}>
          <Text style={[styles.title, { color: textColor }]}>{title}</Text>
          <Text style={[styles.subtitle, { color: mutedColor }]}>{subtitle}</Text>
        </View>

        {!showSaveBar && formError ? (
          <View style={[styles.feedbackCard, { backgroundColor: cardColor, borderColor: '#fecaca' }]}>
            <Text style={[styles.feedbackTitle, { color: textColor }]}>Unable to save changes</Text>
            <Text style={[styles.feedbackText, { color: mutedColor }]}>{formError}</Text>
          </View>
        ) : null}

        {!showSaveBar && successMessage ? (
          <View style={[styles.feedbackCard, { backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' }]}>
            <Text style={[styles.feedbackTitle, { color: '#166534' }]}>Saved</Text>
            <Text style={[styles.feedbackText, { color: '#166534' }]}>{successMessage}</Text>
          </View>
        ) : null}

        {children}
      </ScrollView>

      {showSaveBar ? (
        <View
          style={[
            styles.saveBar,
            {
              backgroundColor: cardColor,
              borderColor,
              paddingBottom: Math.max(insets.bottom, 16),
            },
          ]}
        >
          {hasFeedback ? (
            <View
              style={[
                styles.inlineFeedback,
                formError
                  ? { backgroundColor: '#fef2f2', borderColor: '#fecaca' }
                  : { backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' },
              ]}
            >
              <Text
                style={[
                  styles.inlineFeedbackTitle,
                  { color: formError ? '#991b1b' : '#166534' },
                ]}
              >
                {formError ? 'Unable to save changes' : 'Saved'}
              </Text>
              <Text
                style={[
                  styles.inlineFeedbackText,
                  { color: formError ? '#991b1b' : '#166534' },
                ]}
                numberOfLines={2}
              >
                {formError || successMessage}
              </Text>
            </View>
          ) : null}

          <View style={styles.saveActionsRow}>
            <Pressable
              accessibilityRole="button"
              onPress={() => router.back()}
              style={[styles.secondaryButton, { borderColor }]}
            >
              <Text style={[styles.secondaryButtonText, { color: textColor }]}>Back</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={() => void onSave()}
              disabled={saving || !isDirty}
              style={[
                styles.primaryButton,
                { backgroundColor: saving || !isDirty ? `${tintColor}55` : tintColor },
              ]}
            >
              <Text style={styles.primaryButtonText}>{saving ? 'Saving...' : saveLabel}</Text>
            </Pressable>
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  content: {
    gap: 16,
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  headerBlock: {
    gap: 6,
  },
  title: {
    fontSize: 26,
    fontWeight: '800',
  },
  subtitle: {
    fontSize: 14,
    lineHeight: 20,
  },
  feedbackCard: {
    borderRadius: 16,
    borderWidth: 1,
    gap: 4,
    padding: 14,
  },
  feedbackTitle: {
    fontSize: 15,
    fontWeight: '800',
  },
  feedbackText: {
    fontSize: 13,
    lineHeight: 19,
  },
  saveBar: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    borderTopWidth: 1,
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 10,
  },
  inlineFeedback: {
    borderRadius: 12,
    borderWidth: 1,
    gap: 3,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  inlineFeedbackTitle: {
    fontSize: 13,
    fontWeight: '800',
  },
  inlineFeedbackText: {
    fontSize: 12,
    lineHeight: 17,
  },
  saveActionsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  secondaryButton: {
    flex: 1,
    minHeight: 46,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  primaryButton: {
    flex: 1,
    minHeight: 46,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
});
