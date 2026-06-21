import { useCallback, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import BottomSheet, {
  BottomSheetBackdrop,
  BottomSheetScrollView,
} from '@gorhom/bottom-sheet';
import Markdown from 'react-native-markdown-display';

import {
  askOpportunityAssistant,
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

  if (!visible) return null;

  const answer = String(result?.answer || '').trim();

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
});
