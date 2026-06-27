import { AlertCircle, FileText, Maximize2, Upload, X, Minimize2 } from 'lucide-react';
import { Button } from '../../../../components/ui/button.jsx';
import { useState, useEffect, useRef } from 'react';
import {
  CopyMessageButton,
  StreamingMarkdownMessage,
  ThinkingLoader,
} from './ResumeMatchMessageParts.jsx';
import {
  OpportunityAssistantComposer,
  OpportunityAssistantMessages,
} from './OpportunityAssistantChat.jsx';
import { ALLOWED_RESUME_ACCEPT } from '../../../profile/profileValidation.js';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import { downloadCoverLetterDocx, downloadOptimizedAtsCv } from '../../services/opportunitiesService.js';

const getResumeFileName = (resume, fallback = 'Uploaded resume') =>
  resume?.metadata?.original_filename || resume?.file?.name || fallback;

const getResumeUrl = (resume) => resume?.file_url || resume?.previewUrl || '';

const isPreviewableInline = (resume) => {
  const fileName = getResumeFileName(resume).toLowerCase();
  const contentType = resume?.metadata?.content_type || resume?.file?.type || '';
  return fileName.endsWith('.pdf') || fileName.endsWith('.txt') || contentType === 'application/pdf' || contentType === 'text/plain';
};

const getAnalysisMarkdown = (resumeMatch, aiAnalysis) =>
  aiAnalysis?.analysis?.analysis_markdown ||
  aiAnalysis?.analysis_markdown ||
  resumeMatch?.deterministic_analysis?.analysis_markdown ||
  resumeMatch?.analysis_markdown ||
  '';

const getStatusMessage = (resumeMatch, t) => {
  if (!resumeMatch) return '';
  if (resumeMatch.has_resume === false) {
    return t('opportunities.detail.uploadResumeToCompare');
    }
  if (resumeMatch.status && resumeMatch.status !== 'READY') {
    return t('opportunities.detail.resumeProcessing');
  }
  return '';
};

const getActionLabels = (t) => ({
  optimize_cv: t('opportunities.detail.optimizeCv'),
  rewrite_summary: t('opportunities.detail.rewriteSummary'),
  generate_cover_letter: t('opportunities.detail.generateCoverLetter'),
  interview_prep: t('opportunities.detail.interviewPrep'),
});

const getActionLoadingMessages = (t) => ({
  optimize_cv: t('opportunities.detail.optimizingCv'),
  rewrite_summary: t('opportunities.detail.rewritingSummary'),
  generate_cover_letter: t('opportunities.detail.generatingCoverLetter'),
  interview_prep: t('opportunities.detail.preparingInterview'),
});

const getActionSuggestions = (t) => [
  { key: 'optimize_cv', label: t('opportunities.detail.optimizeCv') },
  { key: 'rewrite_summary', label: t('opportunities.detail.rewriteMySummary') },
  { key: 'generate_cover_letter', label: t('opportunities.detail.generateAMotivationLetter') },
  { key: 'interview_prep', label: t('opportunities.detail.interviewPrep') },
];

const getAnalysisSteps = (t) => [
  t('opportunities.detail.readingResumeSignals'),
  t('opportunities.detail.comparingJobRequirements'),
  t('opportunities.detail.checkingAtsKeywords'),
  t('opportunities.detail.preparingRecommendations'),
];

const getActionSteps = (t) => {
  const analysisSteps = getAnalysisSteps(t);
  return {
    optimize_cv: analysisSteps,
    rewrite_summary: analysisSteps,
    generate_cover_letter: analysisSteps,
    interview_prep: analysisSteps,
  };
};

const ResumeMatchPanel = ({
  resumeMatch,
  loading = false,
  error = '',
  aiAnalysis,
  aiLoading = false,
  aiError = '',
  actionResults = [],
  actionLoading = '',
  actionError = '',
  uploadState = { status: 'idle', resume: null, error: '' },
  onClose,
  onGenerateAnalysis,
  onAction,
  onUploadResume,
  onCancelResumeUpload,
  onConfirmResumeUpload,
  chatMessages = [],
  chatLoading = false,
  chatError = '',
  onSendQuestion,
}) => {
  const { t } = useLanguage();
  const [isMinimized, setIsMinimized] = useState(false);
  const [pendingSuggestionKey, setPendingSuggestionKey] = useState('');
  const [downloadLoadingId, setDownloadLoadingId] = useState('');
  const [downloadError, setDownloadError] = useState('');
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const latestActionRef = useRef(null);
  const latestChatThreadRef = useRef(null);
  const scrollContainerRef = useRef(null);

  const deterministicMarkdown = getAnalysisMarkdown(resumeMatch, null);
  const isAiFallback =
    aiAnalysis?.status === 'fallback' ||
    aiAnalysis?.source === 'deterministic' ||
    aiAnalysis?.analysis?.source === 'deterministic';
  const hasNoResume = resumeMatch?.has_resume === false;
  const resumeMatchReady = resumeMatch?.status === 'READY';
  const aiMarkdown = resumeMatchReady && !hasNoResume && !isAiFallback
    ? aiAnalysis?.analysis?.analysis_markdown || aiAnalysis?.analysis_markdown || ''
    : '';
  const actionMessages = resumeMatchReady && !hasNoResume && Array.isArray(actionResults)
    ? actionResults
        .map((item) => {
          const data = item?.data || item || {};
          const markdown = data?.analysis?.analysis_markdown || data?.analysis_markdown || '';
          return {
            id: item?.id || `${item?.action || data?.action || 'action'}-${markdown.length}`,
            action: item?.action || data?.action || '',
            markdown,
          };
        })
        .filter((item) => item.markdown)
    : [];
  const fallbackMessage = isAiFallback && resumeMatchReady && !hasNoResume
    ? aiAnalysis?.error || t('opportunities.detail.fullAiUnavailable')
    : '';
  const shouldShowDeterministic =
    Boolean(deterministicMarkdown) &&
    resumeMatchReady &&
    !hasNoResume &&
    !aiMarkdown &&
    !aiLoading &&
    !loading;
  const statusMessage = getStatusMessage(resumeMatch, t);
  const actionLabels = getActionLabels(t);
  const actionLoadingMessages = getActionLoadingMessages(t);
  const actionSuggestions = getActionSuggestions(t);
  const analysisSteps = getAnalysisSteps(t);
  const actionSteps = getActionSteps(t);
  const uploadBusy =
    uploadState?.status === 'uploading' ||
    uploadState?.status === 'confirming' ||
    uploadState?.status === 'processing';
  const uploadProcessing = uploadState?.status === 'processing';
  const pendingResume = uploadState?.resume || null;

  const handleDownloadOptimizedCv = async (message) => {
    const opportunityId = resumeMatch?.evidence?.opportunity?.id || resumeMatch?.opportunity_id;
    if (!message?.content || !opportunityId) {
      return;
    }
    setDownloadError('');
    setDownloadLoadingId(message.id);
    try {
      const { blob, filename } = await downloadOptimizedAtsCv(opportunityId, message.content);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      setDownloadError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          'Could not generate the DOCX file.',
      );
    } finally {
      setDownloadLoadingId('');
    }
  };

  const handleDownloadCoverLetter = async (message) => {
    const opportunityId = resumeMatch?.evidence?.opportunity?.id || resumeMatch?.opportunity_id;
    if (!message?.content || !opportunityId) {
      return;
    }
    setDownloadError('');
    setDownloadLoadingId(message.id);
    try {
      const { blob, filename } = await downloadCoverLetterDocx(opportunityId, message.content);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      setDownloadError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          'Could not generate the DOCX file.',
      );
    } finally {
      setDownloadLoadingId('');
    }
  };

  // Keep the user at the start of the newest generated block, not at the composer.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }, [
    deterministicMarkdown,
    aiMarkdown,
    aiLoading,
  ]);

  useEffect(() => {
    latestActionRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }, [
    actionMessages.length,
    actionLoading,
  ]);

  useEffect(() => {
    latestChatThreadRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }, [
    chatMessages.length,
    chatLoading,
  ]);

  // Minimized state - Wide block with large rounded corners
  if (isMinimized) {
    return (
      <div className="fixed bottom-1 right-10 z-50 max-[900px]:inset-x-3">
        <div
          className="flex w-[560px] max-w-[calc(100vw-2rem)] animate-in fade-in slide-in-from-bottom-2 items-center justify-between rounded-2xl bg-white px-5 py-3 shadow-lg ring-1 ring-gray-200 transition-all duration-300 hover:shadow-xl hover:ring-gray-300"
        >
          <div className="flex flex-col items-start">
            <span className="text-base font-semibold text-gray-900">{t('opportunities.detail.bidwiseAi')}</span>
            <span className="text-[10px] text-gray-400">{t('opportunities.detail.beta')}</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setIsMinimized(false)}
              className="rounded-md p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
              aria-label={t('opportunities.detail.openBidwiseAi')}
              title={t('opportunities.detail.open')}
            >
              <Maximize2 className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
              aria-label={t('opportunities.detail.closeBidwiseAi')}
              title={t('opportunities.detail.close')}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed bottom-4 right-10 top-24 z-50 max-[900px]:inset-x-3 max-[900px]:bottom-3 max-[900px]:top-20"
      role="dialog"
      aria-modal="true"
    >
      <section className="flex h-full w-[560px] max-w-[calc(100vw-2rem)] animate-in fade-in slide-in-from-bottom-2 flex-col overflow-hidden rounded-xl bg-white shadow-xl ring-1 ring-gray-200 transition-all duration-300">
        {/* Header - Fixed, never hidden */}
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-100 bg-white px-5 py-3">
          <div className="flex items-center gap-2">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">{t('opportunities.detail.bidwiseAi')}</h3>
              <p className="text-[10px] uppercase tracking-wide text-gray-400">{t('opportunities.detail.beta')}</p>
            </div>
          </div>
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => setIsMinimized(true)}
              className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              aria-label={t('opportunities.detail.minimize')}
            >
              <Minimize2 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={onClose}
              className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              aria-label={t('opportunities.detail.close')}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </header>

        {/* Messages - Fixed height with independent scroll */}
        <div
          ref={scrollContainerRef}
          className="min-h-0 flex-1 overflow-y-auto bg-gray-50 px-4 py-4"
        >
          <div className="flex flex-col">
            {!hasNoResume && resumeMatch ? (
              <div className="mb-4 flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2">
                  <p className="text-sm text-white">{t('opportunities.detail.resumeGoodMatchQuestion')}</p>
                </div>
              </div>
            ) : null}

            {/* Assistant Response Area */}
            <div className="flex justify-start">
              <div className="max-w-[94%]">

                {hasNoResume ? (
                  <div className="rounded-2xl rounded-tl-md bg-white px-5 py-4 shadow-sm ring-1 ring-gray-100">
                    <h4 className="text-base font-semibold text-gray-950">{t('opportunities.detail.welcomeAi')}</h4>
                    <p className="mt-2 text-sm leading-6 text-gray-700">
                      {t('opportunities.detail.welcomeAiBody')}
                    </p>
                    <p className="mt-3 text-sm font-medium text-gray-900">{t('opportunities.detail.letsGetStarted')}</p>

                    <input
                      ref={fileInputRef}
                      type="file"
                      accept={ALLOWED_RESUME_ACCEPT}
                      className="hidden"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) {
                          onUploadResume?.(file);
                          event.target.value = '';
                        }
                      }}
                    />

                    {uploadState?.error ? (
                      <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-100">
                        {uploadState.error}
                      </div>
                    ) : null}

                    {uploadState?.status === 'uploading' ? (
                      <div className="mt-4">
                        <ThinkingLoader
                          label={t('opportunities.detail.uploadingResume')}
                          steps={[t('opportunities.detail.uploadingFile'), t('opportunities.detail.preparingPreview')]}
                        />
                      </div>
                    ) : null}

                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploadBusy}
                      className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                    >
                      <Upload className="mr-2 inline h-4 w-4" />
                      {t('profile.uploadResume')}
                    </button>
                  </div>
                ) : null}

                {hasNoResume && ['confirm', 'confirming'].includes(uploadState?.status) && pendingResume ? (
                  <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/40 px-4 py-6">
                    <div className="w-full max-w-2xl rounded-lg border border-neutral-200 bg-white shadow-2xl">
                      <div className="flex items-center justify-between border-b border-neutral-200 px-5 py-4">
                        <h3 className="text-base font-semibold text-neutral-950">{t('opportunities.detail.resumePreview')}</h3>
                        <button
                          type="button"
                          onClick={onCancelResumeUpload}
                          className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
                          aria-label={t('opportunities.detail.closeResumePreview')}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      <div className="space-y-4 p-5">
                        <div className="flex items-center gap-3 rounded-md border border-neutral-200 bg-neutral-50 p-3">
                          <FileText className="h-5 w-5 text-neutral-500" />
                          <p className="min-w-0 truncate text-sm font-medium text-neutral-900">
                            {getResumeFileName(pendingResume, t('opportunities.detail.uploadedResume'))}
                          </p>
                        </div>

                        {getResumeUrl(pendingResume) && isPreviewableInline(pendingResume) ? (
                          <iframe
                            title={`${t('opportunities.detail.resumePreview')} - ${getResumeFileName(pendingResume, t('opportunities.detail.uploadedResume'))}`}
                            src={getResumeUrl(pendingResume)}
                            referrerPolicy="no-referrer"
                            className="h-80 w-full rounded-md border border-neutral-200 bg-white"
                          />
                        ) : (
                          <div className="flex h-72 items-center justify-center rounded-md border border-neutral-200 bg-neutral-50 p-6 text-center">
                            <div>
                              <FileText className="mx-auto h-10 w-10 text-neutral-400" />
                              <p className="mt-3 text-sm font-medium text-neutral-900">
                                {getResumeFileName(pendingResume, t('opportunities.detail.uploadedResume'))}
                              </p>
                              <p className="mt-1 text-sm text-neutral-500">
                                {t('opportunities.detail.fileReadyUse')}
                              </p>
                            </div>
                          </div>
                        )}

                        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                          <Button type="button" variant="outline" onClick={onCancelResumeUpload}>
                            {t('common.cancel')}
                          </Button>
                          <Button
                            type="button"
                            className="bg-neutral-950 text-white hover:bg-neutral-800"
                            onClick={onConfirmResumeUpload}
                            disabled={uploadState?.status === 'confirming'}
                          >
                            {uploadState?.status === 'confirming' ? t('opportunities.detail.confirming') : t('opportunities.detail.looksGood')}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

                {/* Loading */}
                {!hasNoResume && (loading || uploadProcessing) && !aiMarkdown && !shouldShowDeterministic && (
                  <ThinkingLoader label={t('opportunities.detail.aiReadingResume')} />
                )}

                {/* Error */}
                {!hasNoResume && error && (
                  <div className="flex gap-2 rounded-2xl rounded-tl-md bg-red-50 px-4 py-2.5 ring-1 ring-red-100">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
                    <span className="text-sm text-red-600">{error}</span>
                  </div>
                )}

                {/* Status Message */}
                {!loading && !uploadProcessing && statusMessage && !hasNoResume && (
                  <div className="rounded-2xl rounded-tl-md bg-amber-50 px-4 py-2.5 ring-1 ring-amber-100">
                    <p className="text-sm text-amber-700">{statusMessage}</p>
                  </div>
                )}

                {/* Deterministic Analysis */}
                {shouldShowDeterministic && (
                  <div className="rounded-2xl rounded-tl-md bg-white px-5 py-4 shadow-sm ring-1 ring-gray-100">
                    <div className="-mr-2 -mt-2 mb-1 flex justify-end">
                      <CopyMessageButton markdown={deterministicMarkdown} />
                    </div>
                    <StreamingMarkdownMessage markdown={deterministicMarkdown} />
                  </div>
                )}

                {/* AI Analysis Loading */}
                {resumeMatchReady && !hasNoResume && aiLoading && (
                  <ThinkingLoader label={t('opportunities.detail.aiBuildingMatch')} />
                )}

                {/* AI Analysis Error */}
                {resumeMatchReady && !hasNoResume && aiError && (
                  <div className="flex gap-2 rounded-2xl rounded-tl-md bg-amber-50 px-4 py-2.5 ring-1 ring-amber-100">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                    <span className="text-sm text-amber-600">{aiError}</span>
                  </div>
                )}

                {/* Fallback Message */}
                {fallbackMessage && (
                  <div className="rounded-2xl rounded-tl-md bg-gray-100 px-4 py-2.5">
                    <p className="text-sm text-gray-600">{fallbackMessage}</p>
                  </div>
                )}

                {/* AI Markdown Analysis */}
                {aiMarkdown && (
                  <div className="rounded-2xl rounded-tl-md bg-white px-5 py-4 shadow-sm ring-1 ring-blue-100">
                    <div className="-mr-2 -mt-2 mb-1 flex justify-end">
                      <CopyMessageButton markdown={aiMarkdown} />
                    </div>
                    <StreamingMarkdownMessage markdown={aiMarkdown} />
                  </div>
                )}

                {/* Follow-up action results */}
                {actionMessages.map((message, index) => (
                  <div
                    key={message.id}
                    ref={index === actionMessages.length - 1 ? latestActionRef : null}
                    className="mt-4 scroll-mt-4"
                  >
                    <div className="mb-3 flex justify-end">
                      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2">
                        <p className="text-sm text-white">{actionLabels[message.action] || t('opportunities.detail.runAiAction')}</p>
                      </div>
                    </div>
                    <div className="rounded-2xl rounded-tl-md bg-white px-5 py-4 shadow-sm ring-1 ring-emerald-100">
                      <div className="-mr-2 -mt-2 mb-1 flex justify-end">
                        <CopyMessageButton markdown={message.markdown} />
                      </div>
                      <StreamingMarkdownMessage markdown={message.markdown} />
                    </div>
                  </div>
                ))}

                {/* Follow-up action loading */}
                {resumeMatchReady && !hasNoResume && actionLoading && (
                  <div ref={latestActionRef} className="mt-4 scroll-mt-4">
                    <div className="mb-3 flex justify-end">
                      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2">
                        <p className="text-sm text-white">{actionLabels[actionLoading] || t('opportunities.detail.runAiAction')}</p>
                      </div>
                    </div>
                    <ThinkingLoader
                      label={actionLoadingMessages[actionLoading] || t('opportunities.detail.aiWorking')}
                      steps={actionSteps[actionLoading] || analysisSteps}
                    />
                  </div>
                )}

                {/* Follow-up action error */}
                {resumeMatchReady && !hasNoResume && actionError && (
                  <div className="mt-3 flex gap-2 rounded-2xl rounded-tl-md bg-amber-50 px-4 py-2.5 ring-1 ring-amber-100">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                    <span className="text-sm text-amber-600">{actionError}</span>
                  </div>
                )}

                <OpportunityAssistantMessages
                  messages={chatMessages}
                  loading={chatLoading}
                  error={chatError}
                  onDownloadOptimizedCv={handleDownloadOptimizedCv}
                  onDownloadCoverLetter={handleDownloadCoverLetter}
                  downloadLoadingId={downloadLoadingId}
                  threadStartRef={latestChatThreadRef}
                />

                {downloadError ? (
                  <div className="mt-3 flex gap-2 rounded-2xl rounded-tl-md bg-amber-50 px-4 py-2.5 ring-1 ring-amber-100">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                    <span className="text-sm text-amber-600">{downloadError}</span>
                  </div>
                ) : null}

                <div ref={messagesEndRef} />

                {resumeMatchReady && !hasNoResume && (aiMarkdown || shouldShowDeterministic) && (
                  <div className="mt-4 space-y-2">
                    {actionSuggestions.map((suggestion) => (
                      <button
                        key={suggestion.key}
                        type="button"
                        className={`ml-auto flex w-fit max-w-full rounded-lg border px-4 py-2 text-left text-sm font-medium shadow-sm transition-colors ${
                          pendingSuggestionKey === suggestion.key
                            ? 'border-blue-100 bg-white text-blue-800 ring-1 ring-blue-100'
                            : 'border-gray-200 bg-white text-gray-800 hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-950'
                        }`}
                        onClick={async () => {
                          if (chatLoading || pendingSuggestionKey) return;

                          setPendingSuggestionKey(suggestion.key);
                          try {
                            await onSendQuestion?.(suggestion.label);
                          } finally {
                            setPendingSuggestionKey('');
                          }
                        }}
                      >
                        <span>{suggestion.label}</span>
                      </button>
                    ))}
                  </div>
                )}

              </div>
            </div>
          </div>
        </div>

        <OpportunityAssistantComposer loading={chatLoading} onSendQuestion={onSendQuestion} />
      </section>
    </div>
  );
};

export default ResumeMatchPanel;
