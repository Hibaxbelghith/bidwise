import { memo, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';

import {
  deleteProfileResume,
  uploadProfileResume,
} from '@/src/features/profile/services/profileService';
import type { BidWiseProfile } from '@/src/features/profile/types';

type ResumeSectionProps = {
  profile?: BidWiseProfile;
  onChanged: () => Promise<void>;
  colors: {
    tint: string;
    border: string;
    text: string;
    muted: string;
    card: string;
  };
};

function ResumeSection({ profile, onChanged, colors }: ResumeSectionProps) {
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const activeResume = profile?.active_resume;

  const resumeSignals = useMemo(() => {
    const items: { label: string; value: string; tone?: 'default' | 'warning' | 'success' }[] = [];

    if (activeResume?.uploaded_at) {
      items.push({
        label: 'Uploaded',
        value: formatDateTime(activeResume.uploaded_at),
      });
    }

    if (activeResume?.parsing_status) {
      items.push({
        label: 'CV parsing',
        value: formatStatusLabel(activeResume.parsing_status),
        tone:
          activeResume.parsing_status === 'SUCCEEDED'
            ? 'success'
            : activeResume.parsing_status === 'FAILED'
              ? 'warning'
              : 'default',
      });
    }

    if (activeResume?.semantic_resume_status) {
      items.push({
        label: 'Semantic analysis',
        value: formatStatusLabel(activeResume.semantic_resume_status),
        tone:
          activeResume.semantic_resume_status === 'SUCCEEDED'
            ? 'success'
            : activeResume.semantic_resume_status === 'FAILED'
              ? 'warning'
              : 'default',
      });
    }

    if (activeResume?.semantic_resume_confidence != null) {
      items.push({
        label: 'AI confidence',
        value: `${Math.round(Number(activeResume.semantic_resume_confidence) * 100)}%`,
      });
    }

    if (activeResume?.parsed_text_available != null) {
      items.push({
        label: 'Extracted text',
        value: activeResume.parsed_text_available ? 'Available' : 'Not available yet',
        tone: activeResume.parsed_text_available ? 'success' : 'default',
      });
    }

    return items;
  }, [
    activeResume?.parsed_text_available,
    activeResume?.parsing_status,
    activeResume?.semantic_resume_confidence,
    activeResume?.semantic_resume_status,
    activeResume?.uploaded_at,
  ]);

  const resumeStatusSummary = useMemo(() => {
    if (!activeResume) {
      return 'No resume uploaded yet. Add one to strengthen AI recommendations and direct applications.';
    }

    if (activeResume.semantic_resume_status === 'FAILED') {
      return 'Your resume is saved, but the AI analysis did not complete successfully.';
    }

    if (
      activeResume.semantic_resume_status === 'PENDING'
      || activeResume.parsing_status === 'PENDING'
    ) {
      return 'Your resume is uploaded. BidWise is still preparing extraction and semantic signals.';
    }

    if (activeResume.semantic_resume_status === 'SUCCEEDED' || activeResume.parsed_text_available) {
      return 'Your resume is active and available for recommendation, matching, and applications.';
    }

    return 'Your resume is attached to your profile and ready for direct applications.';
  }, [activeResume]);

  const handleUpload = async () => {
    setError('');
    const result = await DocumentPicker.getDocumentAsync({
      type: [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      ],
      copyToCacheDirectory: true,
      multiple: false,
    });

    if (result.canceled || !result.assets?.[0]) return;

    try {
      setUploading(true);
      await uploadProfileResume(result.assets[0]);
      await onChanged();
    } catch (uploadError: any) {
      setError(uploadError?.response?.data?.file?.[0] || 'Resume upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setDeleting(true);
      setError('');
      await deleteProfileResume();
      await onChanged();
    } catch {
      setError('Could not remove the resume.');
    } finally {
      setDeleting(false);
    }
  };

  const handleOpenResume = async () => {
    const url = String(activeResume?.file_url || '').trim();
    if (!url) {
      setError('No resume file is available to preview right now.');
      return;
    }

    try {
      const supported = await Linking.canOpenURL(url);
      if (!supported) {
        setError('This resume file cannot be opened on your device.');
        return;
      }
      await Linking.openURL(url);
    } catch {
      setError('Could not open the uploaded resume.');
    }
  };

  const confirmDelete = () => {
    Alert.alert(
      'Remove resume?',
      'This will remove the active resume from your profile and direct applications.',
      [
        { text: 'Keep', style: 'cancel' },
        {
          text: deleting ? 'Removing...' : 'Remove',
          style: 'destructive',
          onPress: () => {
            void handleDelete();
          },
        },
      ],
    );
  };

  return (
    <View style={styles.container}>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <View style={styles.actionsGrid}>
        <Pressable
          accessibilityRole="button"
          onPress={handleUpload}
          disabled={uploading}
          style={({ pressed }) => [
            styles.actionBox,
            {
              borderColor: colors.border,
              backgroundColor: colors.card,
              opacity: pressed ? 0.92 : 1,
            },
          ]}
        >
          <Text style={[styles.actionTitle, { color: colors.text }]}>
            {activeResume ? 'Replace resume' : 'Upload resume'}
          </Text>
          <Text style={[styles.actionDesc, { color: colors.muted }]}>
            PDF or DOCX, up to 5 MB. Used for direct applications and AI matching.
          </Text>
          {uploading ? (
            <ActivityIndicator color={colors.tint} />
          ) : (
            <Text style={[styles.actionLink, { color: colors.tint }]}>
              {activeResume ? 'Choose new file' : 'Choose file'}
            </Text>
          )}
        </Pressable>
      </View>

      <View
        style={[
          styles.summaryCard,
          {
            borderColor: activeResume ? '#86efac' : colors.border,
            backgroundColor: activeResume ? '#f0fdf4' : colors.card,
          },
        ]}
      >
        <View style={styles.summaryHeader}>
          <View style={styles.summaryTextWrap}>
            <Text style={[styles.summaryTitle, { color: activeResume ? '#14532d' : colors.text }]}>
              {activeResume ? 'Active resume attached' : 'Resume not uploaded'}
            </Text>
            <Text style={[styles.summaryDesc, { color: activeResume ? '#166534' : colors.muted }]}>
              {activeResume?.metadata?.original_filename || resumeStatusSummary}
            </Text>
          </View>
        </View>

        <Text style={[styles.summaryHint, { color: activeResume ? '#166534' : colors.muted }]}>
          {resumeStatusSummary}
        </Text>

        {activeResume && resumeSignals.length ? (
          <View style={styles.signalGrid}>
            {resumeSignals.map((signal) => (
              <View key={signal.label} style={[styles.signalCard, { borderColor: colors.border }]}>
                <Text style={[styles.signalLabel, { color: colors.muted }]}>{signal.label}</Text>
                <Text
                  style={[
                    styles.signalValue,
                    signal.tone === 'warning'
                      ? { color: '#b45309' }
                      : signal.tone === 'success'
                        ? { color: '#166534' }
                        : { color: colors.text },
                  ]}
                >
                  {signal.value}
                </Text>
              </View>
            ))}
          </View>
        ) : null}

        {activeResume ? (
          <View style={styles.resumeActions}>
            <Pressable
              accessibilityRole="button"
              onPress={() => void handleOpenResume()}
              style={({ pressed }) => [
                styles.secondaryAction,
                { borderColor: colors.border, opacity: pressed ? 0.92 : 1 },
              ]}
            >
              <Text style={[styles.secondaryActionText, { color: colors.text }]}>Open resume</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={confirmDelete}
              style={({ pressed }) => [
                styles.dangerAction,
                { borderColor: '#fca5a5', opacity: pressed ? 0.92 : 1 },
              ]}
            >
              {deleting ? (
                <ActivityIndicator size="small" color="#dc2626" />
              ) : (
                <Text style={styles.dangerActionText}>Remove</Text>
              )}
            </Pressable>
          </View>
        ) : null}
      </View>
    </View>
  );
}

function formatStatusLabel(value: string) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export default memo(ResumeSection);

const styles = StyleSheet.create({
  container: {
    gap: 14,
  },
  actionsGrid: {
    flexDirection: 'row',
    gap: 10,
  },
  actionBox: {
    borderRadius: 12,
    borderWidth: 1,
    flex: 1,
    gap: 8,
    minHeight: 132,
    padding: 14,
  },
  actionTitle: {
    fontSize: 15,
    fontWeight: '800',
  },
  actionDesc: {
    flex: 1,
    fontSize: 12,
    lineHeight: 17,
  },
  actionLink: {
    fontSize: 13,
    fontWeight: '800',
  },
  summaryCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
    gap: 12,
  },
  summaryHeader: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'flex-start',
  },
  summaryTextWrap: {
    flex: 1,
    gap: 4,
  },
  summaryTitle: {
    fontSize: 14,
    fontWeight: '800',
  },
  summaryDesc: {
    fontSize: 13,
    lineHeight: 18,
  },
  summaryHint: {
    fontSize: 13,
    lineHeight: 18,
  },
  signalGrid: {
    gap: 8,
  },
  signalCard: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 4,
  },
  signalLabel: {
    fontSize: 11,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  signalValue: {
    fontSize: 13,
    fontWeight: '700',
  },
  resumeActions: {
    flexDirection: 'row',
    gap: 10,
  },
  secondaryAction: {
    flex: 1,
    minHeight: 42,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 12,
  },
  secondaryActionText: {
    fontSize: 13,
    fontWeight: '700',
  },
  dangerAction: {
    flex: 1,
    minHeight: 42,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 12,
    backgroundColor: '#fef2f2',
  },
  dangerActionText: {
    color: '#dc2626',
    fontSize: 13,
    fontWeight: '700',
  },
  errorText: {
    color: '#dc2626',
    fontSize: 12,
    lineHeight: 17,
  },
});
