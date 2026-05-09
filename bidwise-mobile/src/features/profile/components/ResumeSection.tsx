import { memo, useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';

import { deleteProfileResume, uploadProfileResume } from '@/src/features/profile/services/profileService';
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
  const [showBuilder, setShowBuilder] = useState(false);
  const activeResume = profile?.active_resume;

  const builderSections = useMemo(() => {
    const name = [profile?.prenom, profile?.nom].filter(Boolean).join(' ');
    return [
      { label: 'Identity', value: name || 'Add your name in profile details.' },
      { label: 'Target roles', value: profile?.target_roles?.join(', ') || 'Add target roles.' },
      { label: 'Skills', value: profile?.competences?.join(', ') || 'Add skills.' },
      { label: 'Interests', value: profile?.domaines_interet?.join(', ') || 'Add industries.' },
    ];
  }, [profile]);

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

  return (
    <View style={styles.container}>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <View style={styles.actionsGrid}>
        <TouchableOpacity
          activeOpacity={0.75}
          onPress={handleUpload}
          disabled={uploading}
          style={[styles.actionBox, { borderColor: colors.border, backgroundColor: colors.card }]}
        >
          <Text style={[styles.actionTitle, { color: colors.text }]}>Upload Resume</Text>
          <Text style={[styles.actionDesc, { color: colors.muted }]}>PDF or DOCX, up to 5 MB.</Text>
          {uploading ? <ActivityIndicator color={colors.tint} /> : <Text style={[styles.actionLink, { color: colors.tint }]}>Choose file</Text>}
        </TouchableOpacity>

        <TouchableOpacity
          activeOpacity={0.75}
          onPress={() => setShowBuilder((value) => !value)}
          style={[styles.actionBox, { borderColor: colors.border, backgroundColor: colors.card }]}
        >
          <Text style={[styles.actionTitle, { color: colors.text }]}>Build a BidWise Resume</Text>
          <Text style={[styles.actionDesc, { color: colors.muted }]}>A clean draft from your profile signals.</Text>
          <Text style={[styles.actionLink, { color: colors.tint }]}>{showBuilder ? 'Hide builder' : 'Open builder'}</Text>
        </TouchableOpacity>
      </View>

      {activeResume ? (
        <View style={[styles.activeResume, { borderColor: '#86efac', backgroundColor: '#f0fdf4' }]}>
          <View style={{ flex: 1 }}>
            <Text style={styles.activeTitle}>Active resume attached</Text>
            <Text style={styles.activeDesc}>{activeResume.metadata?.original_filename || 'Uploaded resume'}</Text>
          </View>
          <TouchableOpacity onPress={handleDelete} disabled={deleting} style={styles.removeButton}>
            {deleting ? <ActivityIndicator size="small" color="#166534" /> : <Text style={styles.removeText}>Remove</Text>}
          </TouchableOpacity>
        </View>
      ) : null}

      {showBuilder ? (
        <View style={[styles.builderBox, { borderColor: colors.border, backgroundColor: colors.card }]}>
          {builderSections.map((section) => (
            <View key={section.label} style={styles.builderRow}>
              <Text style={[styles.builderLabel, { color: colors.muted }]}>{section.label}</Text>
              <Text style={[styles.builderValue, { color: colors.text }]}>{section.value}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
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
  activeResume: {
    alignItems: 'center',
    borderRadius: 12,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 12,
    padding: 14,
  },
  activeTitle: {
    color: '#14532d',
    fontSize: 14,
    fontWeight: '800',
  },
  activeDesc: {
    color: '#166534',
    fontSize: 12,
    marginTop: 2,
  },
  removeButton: {
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
  removeText: {
    color: '#166534',
    fontSize: 12,
    fontWeight: '800',
  },
  builderBox: {
    borderRadius: 12,
    borderWidth: 1,
    gap: 12,
    padding: 14,
  },
  builderRow: {
    gap: 4,
  },
  builderLabel: {
    fontSize: 11,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  builderValue: {
    fontSize: 13,
    lineHeight: 18,
  },
  errorText: {
    color: '#dc2626',
    fontSize: 12,
  },
});
