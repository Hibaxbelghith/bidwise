import { useCallback, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import BottomSheet, {
  BottomSheetBackdrop,
  BottomSheetScrollView,
} from '@gorhom/bottom-sheet';
import Markdown from 'react-native-markdown-display';

import {
  askOpportunityAssistant,
  downloadCoverLetterDocx,
  downloadOptimizedAtsCv,
  type OpportunityDocumentDownload,
  type OpportunityAssistantResponse,
} from '../services/opportunitiesService';

type AssistantAction = {
  key: string;
  label: string;
  question: string;
};

type OpportunityAssistantSheetProps = {
  opportunityId?: number | null;
  visible: boolean;
  onClose: () => void;
  colors: {
    background: string;
    card: string;
    border: string;
    text: string;
    muted: string;
    tint: string;
  };
};

const ASSISTANT_ACTIONS: AssistantAction[] = [
  {
    key: 'resume_match',
    label: 'Is my resume a good match?',
    question: 'Is my resume a good match for this role?',
  },
  {
    key: 'optimize_cv',
    label: 'Optimize my CV',
    question: 'Optimize my CV for this role',
  },
  {
    key: 'cover_letter',
    label: 'Generate motivation letter',
    question: 'Generate a motivation letter',
  },
  {
    key: 'interview',
    label: 'Prepare interview questions',
    question: 'Prepare HR interview questions',
  },
];

const getAssistantErrorMessage = (error: any) =>
  error?.response?.data?.detail
  || error?.response?.data?.question?.[0]
  || error?.message
  || 'BidWise AI is temporarily unavailable.';

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = '';

  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }

  return globalThis.btoa(binary);
}

function sanitizeFileName(value: string): string {
  const cleaned = String(value || '')
    .trim()
    .replace(/[\\/:*?"<>|]+/g, '_')
    .replace(/\s+/g, '_');
  return cleaned || 'optimized_ats_resume.docx';
}

type SharingModuleLike = {
  isAvailableAsync?: () => Promise<boolean>;
  shareAsync?: (
    url: string,
    options?: {
      mimeType?: string;
      dialogTitle?: string;
      UTI?: string;
    },
  ) => Promise<void>;
  default?: SharingModuleLike;
};

function normalizeSharingModule(moduleValue: unknown): SharingModuleLike | null {
  if (!moduleValue || typeof moduleValue !== 'object') return null;
  const moduleObject = moduleValue as SharingModuleLike;
  if (typeof moduleObject.shareAsync === 'function') return moduleObject;
  if (moduleObject.default && typeof moduleObject.default.shareAsync === 'function') {
    return moduleObject.default;
  }
  return null;
}

async function writeAndShareDocument(
  document: OpportunityDocumentDownload,
  options: {
    fallbackTitle: string;
    fallbackMessage: string;
    dialogTitle: string;
  },
) {
  const { fallbackTitle, fallbackMessage, dialogTitle } = options;
  const FileSystem = await import('expo-file-system/legacy');
  const filename = sanitizeFileName(document.filename);
  const targetUri = `${FileSystem.cacheDirectory || ''}${filename}`;

  await FileSystem.writeAsStringAsync(targetUri, arrayBufferToBase64(document.bytes), {
    encoding: FileSystem.EncodingType.Base64,
  });

  let Sharing: SharingModuleLike | null = null;
  try {
    Sharing = normalizeSharingModule(await import('expo-sharing'));
  } catch {
    Sharing = null;
  }

  const canShare = Sharing?.isAvailableAsync
    ? await Sharing.isAvailableAsync()
    : Boolean(Sharing?.shareAsync);

  if (Sharing?.shareAsync && canShare) {
    await Sharing.shareAsync(targetUri, {
      mimeType: document.contentType,
      dialogTitle,
      UTI: 'org.openxmlformats.wordprocessingml.document',
    });
    return;
  }

  Alert.alert(fallbackTitle, `${fallbackMessage}\n\n${targetUri}`);
}

export default function OpportunityAssistantSheet({
  opportunityId,
  visible,
  onClose,
  colors,
}: OpportunityAssistantSheetProps) {
  const sheetRef = useRef<BottomSheet>(null);
  const snapPoints = useMemo(() => ['70%', '94%'], []);
  const [selectedAction, setSelectedAction] = useState<AssistantAction | null>(null);
  const [result, setResult] = useState<OpportunityAssistantResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const markdownStyles = useMemo(
    () => ({
      body: {
        color: colors.text,
        fontSize: 14,
        lineHeight: 22,
      },
      heading1: {
        color: colors.text,
        fontSize: 20,
        fontWeight: '800' as const,
      },
      heading2: {
        color: colors.text,
        fontSize: 18,
        fontWeight: '800' as const,
      },
      bullet_list: {
        marginBottom: 8,
      },
      ordered_list: {
        marginBottom: 8,
      },
      strong: {
        color: colors.text,
        fontWeight: '900' as const,
      },
      paragraph: {
        marginTop: 0,
        marginBottom: 8,
      },
    }),
    [colors.text],
  );

  const resetState = useCallback(() => {
    setSelectedAction(null);
    setResult(null);
    setError('');
    setLoading(false);
    setDownloadLoading(false);
    setCopied(false);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [onClose, resetState]);

  const handleSheetChange = useCallback(
    (index: number) => {
      if (index < 0) handleClose();
    },
    [handleClose],
  );

  const runAction = useCallback(
    async (action: AssistantAction) => {
      if (!opportunityId || loading) return;

      try {
        setSelectedAction(action);
        setResult(null);
        setError('');
        setCopied(false);
        setLoading(true);
        const data = await askOpportunityAssistant(opportunityId, action.question);
        setResult(data);
      } catch (requestError: any) {
        setError(getAssistantErrorMessage(requestError));
      } finally {
        setLoading(false);
      }
    },
    [loading, opportunityId],
  );

  const handleCopyAnswer = useCallback(async () => {
    const answerText = String(result?.answer || '').trim();
    if (!answerText) return;

    try {
      const Clipboard = await import('expo-clipboard');
      await Clipboard.setStringAsync(answerText);
      setCopied(true);
    } catch {
      setError('Copy is unavailable in this development build. Rebuild the app to enable clipboard support.');
    }
  }, [result?.answer]);

  const handleDownloadAtsResume = useCallback(async () => {
    const answerText = String(result?.answer || '').trim();
    if (!opportunityId || !answerText || downloadLoading) return;

    try {
      setError('');
      setDownloadLoading(true);
      const document = await downloadOptimizedAtsCv(opportunityId, answerText);
      await writeAndShareDocument(document, {
        fallbackTitle: 'ATS resume ready',
        fallbackMessage: 'The DOCX was generated successfully.',
        dialogTitle: 'Share ATS resume',
      });
    } catch (requestError: any) {
      setError(
        requestError?.response?.data?.detail
        || requestError?.message
        || 'Could not download the ATS resume.',
      );
    } finally {
      setDownloadLoading(false);
    }
  }, [downloadLoading, opportunityId, result?.answer]);

  const handleDownloadCoverLetter = useCallback(async () => {
    const answerText = String(result?.answer || '').trim();
    if (!opportunityId || !answerText || downloadLoading) return;

    try {
      setError('');
      setDownloadLoading(true);
      const document = await downloadCoverLetterDocx(opportunityId, answerText);
      await writeAndShareDocument(document, {
        fallbackTitle: 'Cover letter ready',
        fallbackMessage: 'The Word letter was generated successfully.',
        dialogTitle: 'Share cover letter',
      });
    } catch (requestError: any) {
      setError(
        requestError?.response?.data?.detail
        || requestError?.message
        || 'Could not download the cover letter.',
      );
    } finally {
      setDownloadLoading(false);
    }
  }, [downloadLoading, opportunityId, result?.answer]);

  if (!visible) return null;

  const answer = String(result?.answer || '').trim();
  const canDownloadAtsResume = Boolean(
    answer
    && (selectedAction?.key === 'optimize_cv' || result?.action === 'optimize_cv'),
  );
  const canDownloadCoverLetter = Boolean(
    answer
    && (selectedAction?.key === 'cover_letter' || result?.action === 'generate_cover_letter'),
  );

  return (
    <BottomSheet
      ref={sheetRef}
      index={0}
      snapPoints={snapPoints}
      enablePanDownToClose
      onChange={handleSheetChange}
      backgroundStyle={{ backgroundColor: colors.card }}
      handleIndicatorStyle={{ backgroundColor: colors.border }}
      backdropComponent={(props) => (
        <BottomSheetBackdrop
          {...props}
          appearsOnIndex={0}
          disappearsOnIndex={-1}
          pressBehavior="close"
        />
      )}
    >
      <BottomSheetScrollView
        style={{ backgroundColor: colors.card }}
        contentContainerStyle={styles.sheetContent}
        showsVerticalScrollIndicator
      >
        <View style={styles.header}>
          <View style={styles.headerText}>
            <Text style={[styles.title, { color: colors.text }]}>BidWise AI assistant</Text>
            <Text style={[styles.subtitle, { color: colors.muted }]}>
              Choose an action for this opportunity.
            </Text>
          </View>
          <Pressable
            accessibilityRole="button"
            onPress={handleClose}
            style={({ pressed }) => [
              styles.closeButton,
              { borderColor: colors.border, opacity: pressed ? 0.8 : 1 },
            ]}
          >
            <Text style={[styles.closeText, { color: colors.muted }]}>Close</Text>
          </Pressable>
        </View>

        <View style={styles.actionGrid}>
          {ASSISTANT_ACTIONS.map((action) => {
            const selected = selectedAction?.key === action.key;
            return (
              <Pressable
                key={action.key}
                accessibilityRole="button"
                disabled={loading}
                onPress={() => void runAction(action)}
                style={({ pressed }) => [
                  styles.actionButton,
                  {
                    borderColor: selected ? colors.tint : colors.border,
                    backgroundColor: selected ? `${colors.tint}18` : colors.background,
                    opacity: pressed || loading ? 0.82 : 1,
                  },
                ]}
              >
                <Text style={[styles.actionText, { color: selected ? colors.tint : colors.text }]}>
                  {action.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View style={[styles.resultBox, { borderColor: colors.border, backgroundColor: colors.background }]}>
          {!selectedAction && !loading && !answer && !error ? (
            <Text style={[styles.emptyText, { color: colors.muted }]}>
              Start with one of the assistant actions above.
            </Text>
          ) : null}

          {loading ? (
            <View style={styles.loadingBox}>
              <ActivityIndicator color={colors.tint} />
              <Text style={[styles.loadingText, { color: colors.muted }]}>
                BidWise AI is preparing your answer...
              </Text>
            </View>
          ) : null}

          {error ? (
            <Text style={styles.errorText}>{error}</Text>
          ) : null}

          {answer ? (
            <>
              <View style={styles.resultActions}>
                <Pressable
                  accessibilityRole="button"
                  onPress={() => void handleCopyAnswer()}
                  style={({ pressed }) => [
                    styles.copyButton,
                    {
                      borderColor: colors.tint,
                      backgroundColor: copied ? `${colors.tint}18` : colors.card,
                      opacity: pressed ? 0.85 : 1,
                    },
                  ]}
                >
                  <Text style={[styles.copyButtonText, { color: colors.tint }]}>
                    {copied ? 'Copied' : 'Copy response'}
                  </Text>
                </Pressable>
              </View>
              {canDownloadAtsResume ? (
                <View style={[styles.downloadCard, { borderColor: colors.tint, backgroundColor: `${colors.tint}10` }]}>
                  <View style={styles.downloadBadge}>
                    <Text style={styles.downloadBadgeText}>DOCX</Text>
                  </View>
                  <View style={styles.downloadCopy}>
                    <Text style={[styles.downloadTitle, { color: colors.text }]}>ATS resume ready</Text>
                    <Text style={[styles.downloadDesc, { color: colors.muted }]}>
                      Editable Word document tailored to this opportunity.
                    </Text>
                  </View>
                  <Pressable
                    accessibilityRole="button"
                    disabled={downloadLoading}
                    onPress={() => void handleDownloadAtsResume()}
                    style={({ pressed }) => [
                      styles.downloadButton,
                      {
                        backgroundColor: colors.tint,
                        opacity: pressed || downloadLoading ? 0.82 : 1,
                      },
                    ]}
                  >
                    {downloadLoading ? (
                      <ActivityIndicator color="#ffffff" />
                    ) : (
                      <Text style={styles.downloadButtonText}>Open / Share resume</Text>
                    )}
                  </Pressable>
                </View>
              ) : null}
              {canDownloadCoverLetter ? (
                <View style={[styles.downloadCard, { borderColor: colors.tint, backgroundColor: `${colors.tint}10` }]}>
                  <View style={styles.downloadBadge}>
                    <Text style={styles.downloadBadgeText}>DOCX</Text>
                  </View>
                  <View style={styles.downloadCopy}>
                    <Text style={[styles.downloadTitle, { color: colors.text }]}>Cover letter ready</Text>
                    <Text style={[styles.downloadDesc, { color: colors.muted }]}>
                      Editable Word letter tailored to this application.
                    </Text>
                  </View>
                  <Pressable
                    accessibilityRole="button"
                    disabled={downloadLoading}
                    onPress={() => void handleDownloadCoverLetter()}
                    style={({ pressed }) => [
                      styles.downloadButton,
                      {
                        backgroundColor: colors.tint,
                        opacity: pressed || downloadLoading ? 0.82 : 1,
                      },
                    ]}
                  >
                    {downloadLoading ? (
                      <ActivityIndicator color="#ffffff" />
                    ) : (
                      <Text style={styles.downloadButtonText}>Open / Share letter</Text>
                    )}
                  </Pressable>
                </View>
              ) : null}
              <View style={styles.markdownContent}>
                <Markdown style={markdownStyles}>{answer}</Markdown>
              </View>
            </>
          ) : null}
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  sheetContent: {
    paddingHorizontal: 16,
    paddingBottom: 32,
    gap: 14,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  headerText: {
    flex: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: '900',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    lineHeight: 18,
  },
  closeButton: {
    borderWidth: 1,
    borderRadius: 999,
    minHeight: 34,
    paddingHorizontal: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeText: {
    fontSize: 12,
    fontWeight: '800',
  },
  actionGrid: {
    gap: 8,
  },
  actionButton: {
    borderWidth: 1,
    borderRadius: 12,
    minHeight: 44,
    paddingHorizontal: 12,
    justifyContent: 'center',
  },
  actionText: {
    fontSize: 14,
    fontWeight: '800',
  },
  resultBox: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    minHeight: 180,
  },
  emptyText: {
    fontSize: 14,
    lineHeight: 20,
  },
  loadingBox: {
    minHeight: 140,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  loadingText: {
    fontSize: 13,
    fontWeight: '700',
  },
  errorText: {
    color: '#b91c1c',
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 19,
  },
  resultActions: {
    alignItems: 'flex-end',
    marginBottom: 8,
  },
  copyButton: {
    borderWidth: 1,
    borderRadius: 999,
    minHeight: 34,
    paddingHorizontal: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copyButtonText: {
    fontSize: 12,
    fontWeight: '900',
  },
  markdownContent: {
    paddingBottom: 24,
  },
  downloadCard: {
    borderWidth: 1,
    borderRadius: 14,
    gap: 12,
    marginBottom: 14,
    padding: 12,
  },
  downloadBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#2563eb',
    borderRadius: 999,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  downloadBadgeText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0.4,
  },
  downloadCopy: {
    gap: 3,
  },
  downloadTitle: {
    fontSize: 14,
    fontWeight: '900',
  },
  downloadDesc: {
    fontSize: 12,
    fontWeight: '600',
    lineHeight: 17,
  },
  downloadButton: {
    alignItems: 'center',
    borderRadius: 12,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: 14,
  },
  downloadButtonText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '900',
  },
});
