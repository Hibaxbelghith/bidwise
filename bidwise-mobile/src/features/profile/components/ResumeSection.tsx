import { memo, useEffect, useMemo, useState } from 'react';
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
import * as WebBrowser from 'expo-web-browser';

import {
  applyResumeProfileSuggestions,
  deleteProfileResume,
  uploadProfileResume,
} from '@/src/features/profile/services/profileService';
import type { BidWiseProfile } from '@/src/features/profile/types';
import {
  normalizeSkillList,
  normalizeTextList,
} from '@/src/features/profile/utils/profileValidation';
import { getProfileResumeDisplayName } from '@/src/features/profile/utils/resumeDisplay';

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

const MAX_PROFILE_SKILLS = 30;

const RESUME_STATUS_LABELS: Record<string, string> = {
  PENDING: 'In progress',
  PROCESSING: 'In progress',
  SUCCEEDED: 'Ready',
  COMPLETED: 'Ready',
  FAILED: 'Needs review',
  EMPTY: 'No content detected',
  SKIPPED: 'Skipped',
};

function getResumeFileName(profile?: BidWiseProfile) {
  return getProfileResumeDisplayName(profile, '');
}

function isResumePreviewable(profile?: BidWiseProfile) {
  const fileName = getResumeFileName(profile).toLowerCase();
  const contentType = String(profile?.active_resume?.metadata?.content_type || '').toLowerCase();
  return (
    fileName.endsWith('.pdf')
    || fileName.endsWith('.txt')
    || contentType === 'application/pdf'
    || contentType === 'text/plain'
  );
}

function hasValue(values: string[], candidate: string) {
  const normalizedCandidate = String(candidate || '').trim().toLowerCase();
  return values.some((value) => value.toLowerCase() === normalizedCandidate);
}

function hasProfileSuggestions(profile?: BidWiseProfile) {
  const suggestions = profile?.active_resume?.profile_suggestions;
  if (!suggestions || typeof suggestions !== 'object') return false;

  return Object.values(suggestions).some((value) =>
    Array.isArray(value) ? value.some(Boolean) : value != null && String(value).trim() !== '',
  );
}

function normalizeStatus(value: string | null | undefined) {
  return String(value || '').trim().toUpperCase();
}

function isResumeAnalysisRunning(profile?: BidWiseProfile) {
  const semanticStatus = normalizeStatus(profile?.active_resume?.semantic_resume_status);
  const parsingStatus = normalizeStatus(profile?.active_resume?.parsing_status);
  return ['PENDING', 'PROCESSING'].includes(semanticStatus) || ['PENDING', 'PROCESSING'].includes(parsingStatus);
}

function isResumeAnalysisDelayed(profile?: BidWiseProfile) {
  if (!isResumeAnalysisRunning(profile)) return false;
  const uploadedAt = String(profile?.active_resume?.uploaded_at || '').trim();
  if (!uploadedAt) return false;
  const uploadedDate = new Date(uploadedAt);
  if (Number.isNaN(uploadedDate.getTime())) return false;
  return Date.now() - uploadedDate.getTime() >= 120000;
}

function ResumeSection({ profile, onChanged, colors }: ResumeSectionProps) {
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [applyingSuggestions, setApplyingSuggestions] = useState(false);
  const [error, setError] = useState('');
  const [dismissedSuggestionResumeId, setDismissedSuggestionResumeId] = useState<number | null>(null);
  const [selectedRole, setSelectedRole] = useState('');
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const activeResume = profile?.active_resume;
  const analysisRunning = isResumeAnalysisRunning(profile);
  const analysisDelayed = isResumeAnalysisDelayed(profile);
  const currentRoles = useMemo(() => normalizeTextList(profile?.target_roles), [profile?.target_roles]);
  const currentSkills = useMemo(() => normalizeSkillList(profile?.competences), [profile?.competences]);
  const hasPendingSuggestions = hasProfileSuggestions(profile);
  const suggestedRole = useMemo(() => {
    const firstRole = Array.isArray(activeResume?.profile_suggestions?.target_roles)
      ? String(activeResume?.profile_suggestions?.target_roles?.[0] || '').trim()
      : '';
    return firstRole && !hasValue(currentRoles, firstRole) ? firstRole : '';
  }, [activeResume?.profile_suggestions?.target_roles, currentRoles]);
  const suggestedSkills = useMemo(() => {
    const skillSlots = Math.max(0, MAX_PROFILE_SKILLS - currentSkills.length);
    const rawSkills = Array.isArray(activeResume?.profile_suggestions?.competences)
      ? activeResume.profile_suggestions.competences
      : activeResume?.extracted_skills;
    return normalizeSkillList(rawSkills)
      .filter((skill) => !hasValue(currentSkills, skill))
      .slice(0, skillSlots);
  }, [activeResume?.extracted_skills, activeResume?.profile_suggestions?.competences, currentSkills]);
  const showSuggestionCard =
    Boolean(activeResume?.id)
    && String(activeResume?.semantic_resume_status || '').toUpperCase() === 'SUCCEEDED'
    && hasPendingSuggestions
    && dismissedSuggestionResumeId !== activeResume?.id
    && (Boolean(suggestedRole) || suggestedSkills.length > 0);

  useEffect(() => {
    if (!activeResume?.id) {
      setDismissedSuggestionResumeId(null);
      setSelectedRole('');
      setSelectedSkills([]);
      return;
    }

    if (!showSuggestionCard) {
      setSelectedRole('');
      setSelectedSkills([]);
      return;
    }

    setSelectedRole(suggestedRole);
    setSelectedSkills(suggestedSkills);
  }, [activeResume?.id, showSuggestionCard, suggestedRole, suggestedSkills]);

  useEffect(() => {
    if (!analysisRunning || !activeResume?.id) {
      return undefined;
    }

    const refreshInterval = setInterval(() => {
      void onChanged();
    }, 5000);

    return () => clearInterval(refreshInterval);
  }, [activeResume?.id, analysisRunning, onChanged]);

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
        label: 'Text extraction',
        value: formatResumeStatus(activeResume.parsing_status),
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
        label: 'AI analysis',
        value: formatResumeStatus(activeResume.semantic_resume_status),
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

    return items;
  }, [
    activeResume?.parsing_status,
    activeResume?.semantic_resume_confidence,
    activeResume?.semantic_resume_status,
    activeResume?.uploaded_at,
  ]);

  const resumeStatusSummary = useMemo(() => {
    if (!activeResume) {
      return 'Upload a PDF or DOCX to strengthen AI matching and direct applications.';
    }

    if (activeResume.semantic_resume_status === 'FAILED') {
      return 'Your resume is saved, but the AI analysis did not complete successfully.';
    }

    if (
      activeResume.semantic_resume_status === 'PENDING'
      || activeResume.parsing_status === 'PENDING'
    ) {
      return 'Your resume is uploaded. BidWise is still preparing extraction and AI matching signals.';
    }

    if (activeResume.semantic_resume_status === 'SUCCEEDED' || activeResume.parsed_text_available) {
      return 'Your resume is active and ready for recommendations, matching, and applications.';
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
      setError('No resume file is available right now.');
      return;
    }

    try {
      if (isResumePreviewable(profile)) {
        await WebBrowser.openBrowserAsync(url);
      } else {
        const supported = await Linking.canOpenURL(url);
        if (!supported) {
          setError('This resume file cannot be opened on your device.');
          return;
        }
        await Linking.openURL(url);
      }
    } catch {
      setError('Could not open the uploaded resume.');
    }
  };

  const handleToggleRole = () => {
    setSelectedRole((current) => (current ? '' : suggestedRole));
  };

  const handleToggleSkill = (skill: string) => {
    setSelectedSkills((current) =>
      current.includes(skill)
        ? current.filter((value) => value !== skill)
        : [...current, skill].slice(0, Math.max(0, MAX_PROFILE_SKILLS - currentSkills.length)),
    );
  };

  const handleDismissSuggestions = () => {
    setDismissedSuggestionResumeId(activeResume?.id || null);
    setSelectedRole('');
    setSelectedSkills([]);
  };

  const handleApplySuggestions = async () => {
    if (!activeResume?.id) return;

    const selected: Record<string, unknown> = {};
    if (selectedRole) {
      selected.target_roles = [selectedRole];
    }
    if (selectedSkills.length) {
      selected.competences = selectedSkills;
    }

    if (!Object.keys(selected).length) {
      handleDismissSuggestions();
      return;
    }

    try {
      setApplyingSuggestions(true);
      setError('');
      await applyResumeProfileSuggestions(activeResume.id, selected);
      handleDismissSuggestions();
      await onChanged();
    } catch (applyError: any) {
      setError(
        applyError?.response?.data?.detail
        || applyError?.response?.data?.selected?.[0]
        || 'Could not apply resume suggestions.',
      );
    } finally {
      setApplyingSuggestions(false);
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

      {activeResume && analysisRunning && !analysisDelayed ? (
        <View style={styles.analysisCard}>
          <View style={styles.analysisIcon}>
            <ActivityIndicator color={colors.tint} />
          </View>
          <View style={styles.analysisBody}>
            <Text style={[styles.analysisTitle, { color: colors.text }]}>Analyzing your resume...</Text>
            <View style={styles.analysisTrack}>
              <View style={[styles.analysisFill, { backgroundColor: colors.tint }]} />
            </View>
            <Text style={[styles.analysisText, { color: colors.muted }]}>
              BidWise is reading the original CV, extracting text, and preparing structured matching signals.
            </Text>
          </View>
        </View>
      ) : null}

      {activeResume && analysisDelayed ? (
        <View style={styles.analysisDelayedCard}>
          <Text style={[styles.analysisTitle, { color: '#92400e' }]}>Resume uploaded successfully.</Text>
          <Text style={[styles.analysisText, { color: '#92400e' }]}>
            AI analysis is taking longer than expected. Your recommendations will improve once extraction completes.
          </Text>
        </View>
      ) : null}

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
              {activeResume ? 'Active resume attached' : 'No resume uploaded yet'}
            </Text>
            <Text style={[styles.summaryDesc, { color: activeResume ? '#166534' : colors.muted }]}>
              {getProfileResumeDisplayName(profile, resumeStatusSummary)}
            </Text>
          </View>
        </View>

        {activeResume ? (
          <Text style={[styles.summaryHint, { color: '#166534' }]}>
            {resumeStatusSummary}
          </Text>
        ) : null}

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
          <View style={[styles.extractionNoteCard, { borderColor: colors.border }]}>
            <Text style={[styles.extractionNoteTitle, { color: colors.text }]}>Original CV vs extracted signals</Text>
            <Text style={[styles.extractionNoteText, { color: colors.muted }]}>
              The uploaded file is your original resume. Extraction means BidWise reads that file and derives text, skills, and role signals used for matching and recommendations.
            </Text>
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
              <Text style={[styles.secondaryActionText, { color: colors.text }]}>
                {isResumePreviewable(profile) ? 'Preview resume' : 'Download resume'}
              </Text>
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

      {showSuggestionCard ? (
        <View style={[styles.suggestionCard, { borderColor: '#bfdbfe', backgroundColor: '#eff6ff' }]}>
          <View style={styles.suggestionHeader}>
            <Text style={[styles.suggestionTitle, { color: '#1d4ed8' }]}>
              Add CV suggestions to your profile?
            </Text>
            <Text style={[styles.suggestionText, { color: '#1e3a8a' }]}>
              Review the role and skills detected from your resume before adding them.
            </Text>
          </View>

          {suggestedRole ? (
            <View style={styles.suggestionBlock}>
              <Text style={[styles.suggestionLabel, { color: colors.muted }]}>Detected role</Text>
              <Pressable
                accessibilityRole="button"
                onPress={handleToggleRole}
                style={[
                  styles.selectionChip,
                  {
                    borderColor: selectedRole ? colors.tint : colors.border,
                    backgroundColor: selectedRole ? `${colors.tint}16` : colors.card,
                  },
                ]}
              >
                <Text style={[styles.selectionChipText, { color: selectedRole ? colors.tint : colors.text }]}>
                  {suggestedRole}
                </Text>
              </Pressable>
            </View>
          ) : null}

          {suggestedSkills.length ? (
            <View style={styles.suggestionBlock}>
              <Text style={[styles.suggestionLabel, { color: colors.muted }]}>Detected skills</Text>
              <View style={styles.selectionWrap}>
                {suggestedSkills.map((skill) => {
                  const active = selectedSkills.includes(skill);
                  return (
                    <Pressable
                      key={skill}
                      accessibilityRole="button"
                      onPress={() => handleToggleSkill(skill)}
                      style={[
                        styles.selectionChip,
                        {
                          borderColor: active ? colors.tint : colors.border,
                          backgroundColor: active ? `${colors.tint}16` : colors.card,
                        },
                      ]}
                    >
                      <Text style={[styles.selectionChipText, { color: active ? colors.tint : colors.text }]}>
                        {skill}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
          ) : null}

          <View style={styles.resumeActions}>
            <Pressable
              accessibilityRole="button"
              onPress={handleDismissSuggestions}
              disabled={applyingSuggestions}
              style={({ pressed }) => [
                styles.secondaryAction,
                { borderColor: colors.border, opacity: pressed ? 0.92 : 1 },
              ]}
            >
              <Text style={[styles.secondaryActionText, { color: colors.text }]}>Skip</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={() => void handleApplySuggestions()}
              disabled={applyingSuggestions || (!selectedRole && !selectedSkills.length)}
              style={({ pressed }) => [
                styles.primaryAction,
                {
                  backgroundColor:
                    applyingSuggestions || (!selectedRole && !selectedSkills.length)
                      ? `${colors.tint}55`
                      : colors.tint,
                  opacity: pressed ? 0.92 : 1,
                },
              ]}
            >
              {applyingSuggestions ? (
                <ActivityIndicator size="small" color="#ffffff" />
              ) : (
                <Text style={styles.primaryActionText}>Add selected</Text>
              )}
            </Pressable>
          </View>
        </View>
      ) : null}
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

function formatResumeStatus(value: string) {
  const normalized = String(value || '').trim().toUpperCase();
  return RESUME_STATUS_LABELS[normalized] || formatStatusLabel(value);
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
  analysisCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#dbeafe',
    backgroundColor: '#eff6ff',
    padding: 14,
    flexDirection: 'row',
    gap: 12,
    alignItems: 'flex-start',
  },
  analysisDelayedCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#fde68a',
    backgroundColor: '#fffbeb',
    padding: 14,
    gap: 6,
  },
  analysisIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  analysisBody: {
    flex: 1,
    gap: 8,
  },
  analysisTitle: {
    fontSize: 14,
    fontWeight: '800',
  },
  analysisTrack: {
    height: 6,
    borderRadius: 999,
    backgroundColor: '#dbeafe',
    overflow: 'hidden',
  },
  analysisFill: {
    width: '52%',
    height: '100%',
    borderRadius: 999,
  },
  analysisText: {
    fontSize: 13,
    lineHeight: 18,
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
  suggestionCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
    gap: 12,
  },
  suggestionHeader: {
    gap: 4,
  },
  suggestionTitle: {
    fontSize: 14,
    fontWeight: '800',
  },
  suggestionText: {
    fontSize: 13,
    lineHeight: 18,
  },
  suggestionBlock: {
    gap: 8,
  },
  suggestionLabel: {
    fontSize: 11,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  selectionWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  selectionChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  selectionChipText: {
    fontSize: 13,
    fontWeight: '700',
  },
  signalGrid: {
    gap: 8,
  },
  extractionNoteCard: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 4,
    backgroundColor: '#ffffff',
  },
  extractionNoteTitle: {
    fontSize: 12,
    fontWeight: '800',
  },
  extractionNoteText: {
    fontSize: 12,
    lineHeight: 17,
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
  primaryAction: {
    flex: 1,
    minHeight: 42,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 12,
  },
  primaryActionText: {
    color: '#ffffff',
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
