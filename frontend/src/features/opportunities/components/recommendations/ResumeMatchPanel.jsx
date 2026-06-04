import { AlertCircle, Loader2, Maximize2, Sparkles, X, Minimize2, Zap } from 'lucide-react';
import { Button } from '../../../../components/ui/button.jsx';
import { useState, useEffect, useRef } from 'react';
import {
  CopyMessageButton,
  StreamingMarkdownMessage,
  ThinkingLoader,
} from './ResumeMatchMessageParts.jsx';

const getAnalysisMarkdown = (resumeMatch, aiAnalysis) =>
  aiAnalysis?.analysis?.analysis_markdown ||
  aiAnalysis?.analysis_markdown ||
  resumeMatch?.deterministic_analysis?.analysis_markdown ||
  resumeMatch?.analysis_markdown ||
  '';

const getStatusMessage = (resumeMatch) => {
  if (!resumeMatch) return '';
  if (resumeMatch.has_resume === false) {
    return 'Upload your resume to compare it with this opportunity.';
    }
  if (resumeMatch.status && resumeMatch.status !== 'READY') {
    return 'Your resume is still being processed. Try again once the resume analysis is ready.';
  }
  return '';
};

const ACTION_LABELS = {
  optimize_cv: 'Optimize my CV for this role',
  rewrite_summary: 'Rewrite professional summary',
  generate_cover_letter: 'Generate motivation letter',
  interview_prep: 'Prepare HR interview questions',
};

const ACTION_LOADING_MESSAGES = {
  optimize_cv: 'Optimizing your CV for this role...',
  rewrite_summary: 'Rewriting your professional summary...',
  generate_cover_letter: 'Generating your motivation letter...',
  interview_prep: 'Preparing interview questions...',
};

const ACTION_SUGGESTIONS = [
  { key: 'optimize_cv', label: 'Optimize my CV for this role' },
  { key: 'rewrite_summary', label: 'Rewrite my professional summary' },
  { key: 'generate_cover_letter', label: 'Generate a motivation letter' },
  { key: 'interview_prep', label: 'Prepare HR interview questions' },
];

const ANALYSIS_STEPS = [
  'Reading resume signals',
  'Comparing job requirements',
  'Checking ATS keywords',
  'Preparing recommendations',
];

const ACTION_STEPS = {
  optimize_cv: ['Reviewing resume sections', 'Prioritizing ATS keywords', 'Drafting stronger CV wording'],
  rewrite_summary: ['Reading profile evidence', 'Selecting safe keywords', 'Writing summary options'],
  generate_cover_letter: ['Mapping your strengths', 'Personalizing the letter', 'Preparing short version'],
  interview_prep: ['Scanning role gaps', 'Drafting likely questions', 'Building answer strategy'],
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
  onClose,
  onGenerateAnalysis,
  onAction,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const messagesEndRef = useRef(null);
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
    ? aiAnalysis?.error || 'Full AI analysis is not available right now. Showing quick analysis instead.'
    : '';
  const shouldShowDeterministic = Boolean(deterministicMarkdown) && resumeMatchReady && !hasNoResume && !aiMarkdown && !aiLoading;
  const statusMessage = getStatusMessage(resumeMatch);
  const canGenerateAiAnalysis =
    Boolean(resumeMatch?.can_generate_ai_analysis) &&
    resumeMatchReady &&
    !hasNoResume &&
    !aiLoading &&
    (!aiAnalysis || isAiFallback) &&
    !aiAnalysis?.analysis_markdown;

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [deterministicMarkdown, aiMarkdown, actionMessages.length, aiLoading, actionLoading]);

  // Minimized state - Wide block with large rounded corners
  if (isMinimized) {
    return (
      <div className="fixed bottom-1 right-10 z-50 max-[900px]:inset-x-3">
        <div
          className="flex w-[560px] max-w-[calc(100vw-2rem)] animate-in fade-in slide-in-from-bottom-2 items-center justify-between rounded-2xl bg-white px-5 py-3 shadow-lg ring-1 ring-gray-200 transition-all duration-300 hover:shadow-xl hover:ring-gray-300"
        >
          <div className="flex flex-col items-start">
            <span className="text-base font-semibold text-gray-900">BidWise AI</span>
            <span className="text-[10px] text-gray-400">Beta</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setIsMinimized(false)}
              className="rounded-md p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
              aria-label="Open BidWise AI"
              title="Open"
            >
              <Maximize2 className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
              aria-label="Close BidWise AI"
              title="Close"
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
              <h3 className="text-sm font-semibold text-gray-900">BidWise AI</h3>
              <p className="text-[10px] uppercase tracking-wide text-gray-400">Beta</p>
            </div>
          </div>
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => setIsMinimized(true)}
              className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              aria-label="Minimize"
            >
              <Minimize2 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={onClose}
              className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              aria-label="Close"
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
                  <p className="text-sm text-white">Is my resume a good match for this role?</p>
                </div>
              </div>
            ) : null}

            {/* Assistant Response Area */}
            <div className="flex justify-start">
              <div className="max-w-[94%]">

                {hasNoResume ? (
                  <div className="rounded-2xl rounded-tl-md bg-white px-5 py-4 shadow-sm ring-1 ring-gray-100">
                    <h4 className="text-base font-semibold text-gray-950">Hi! Welcome to BidWise AI</h4>
                    <p className="mt-2 text-sm leading-6 text-gray-700">
                      Powered by thousands of opportunities listings, I can bring you smarter recommendations
                      and streamline your career research.
                    </p>
                    <p className="mt-3 text-sm font-medium text-gray-900">Let's get started!</p>
                    <button
                      type="button"
                      onClick={() => {
                        window.location.assign('/profile#resume');
                      }}
                      className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                    >
                      Upload your resume
                    </button>
                  </div>
                ) : null}

                {/* Loading */}
                {!hasNoResume && loading && (
                  <ThinkingLoader label="BidWise AI is reading your resume" />
                )}

                {/* Error */}
                {!hasNoResume && error && (
                  <div className="flex gap-2 rounded-2xl rounded-tl-md bg-red-50 px-4 py-2.5 ring-1 ring-red-100">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
                    <span className="text-sm text-red-600">{error}</span>
                  </div>
                )}

                {/* Status Message */}
                {!loading && statusMessage && !hasNoResume && (
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
                  <ThinkingLoader label="BidWise AI is building the match analysis" />
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
                {actionMessages.map((message) => (
                  <div key={message.id} className="mt-4">
                    <div className="mb-3 flex justify-end">
                      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2">
                        <p className="text-sm text-white">{ACTION_LABELS[message.action] || 'Run AI assistant action'}</p>
                      </div>
                    </div>
                    <div className="rounded-2xl rounded-tl-md bg-white px-5 py-4 shadow-sm ring-1 ring-emerald-100">
                      <div className="-mr-2 -mt-2 mb-1 flex items-center justify-between gap-3">
                        <span className="text-[11px] font-medium text-emerald-700">
                          {ACTION_LABELS[message.action] || 'AI assistant action'}
                        </span>
                        <CopyMessageButton markdown={message.markdown} />
                      </div>
                      <StreamingMarkdownMessage markdown={message.markdown} />
                    </div>
                  </div>
                ))}

                {/* Follow-up action loading */}
                {resumeMatchReady && !hasNoResume && actionLoading && (
                  <div className="mt-4">
                    <div className="mb-3 flex justify-end">
                      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2">
                        <p className="text-sm text-white">{ACTION_LABELS[actionLoading] || 'Run AI assistant action'}</p>
                      </div>
                    </div>
                    <ThinkingLoader
                      label={ACTION_LOADING_MESSAGES[actionLoading] || 'BidWise AI is working'}
                      steps={ACTION_STEPS[actionLoading] || ANALYSIS_STEPS}
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

                {aiMarkdown && !isAiFallback && (
                  <div className="mt-4 space-y-2">
                    {ACTION_SUGGESTIONS.map((suggestion) => (
                      <button
                        key={suggestion.key}
                        type="button"
                        className={`ml-auto flex w-fit max-w-full rounded-lg border px-4 py-2 text-left text-sm font-medium shadow-sm transition-colors ${
                          actionLoading === suggestion.key
                            ? 'border-blue-100 bg-white text-blue-800 ring-1 ring-blue-100'
                            : 'border-gray-200 bg-white text-gray-800 hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-950'
                        }`}
                        onClick={() => onAction?.(suggestion.key)}
                      >
                        {actionLoading === suggestion.key ? (
                          <Loader2 className="mr-2 h-3.5 w-3.5 shrink-0 animate-spin text-blue-600" />
                        ) : null}
                        <span>{suggestion.label}</span>
                      </button>
                    ))}
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>
          </div>
        </div>

        {/* Footer - Sticky, always visible */}
        {canGenerateAiAnalysis ? (
        <footer className="sticky bottom-0 z-10 border-t border-gray-100 bg-white px-5 py-3">
            <Button
              type="button"
              className="w-full justify-center gap-2 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
              onClick={onGenerateAnalysis}
            >
              Generate full AI analysis
            </Button>
        </footer>
        ) : null}
      </section>
    </div>
  );
};

export default ResumeMatchPanel;
