import {
  AlertCircle,
  ArrowDownToLine,
  FileCheck2,
  Loader2,
  MailCheck,
  Send,
  Sparkles,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import { AssistantRobotLoader, CopyMessageButton, markdownToHtml } from './ResumeMatchMessageParts.jsx';

const DownloadArtifactCard = ({
  variant = 'resume',
  loading = false,
  onDownload,
}) => {
  const { t } = useLanguage();
  const isCoverLetter = variant === 'coverLetter';
  const Icon = isCoverLetter ? MailCheck : FileCheck2;
  const title = isCoverLetter
    ? t('opportunities.detail.coverLetterReadyTitle')
    : t('opportunities.detail.atsCvReadyTitle');
  const body = isCoverLetter
    ? t('opportunities.detail.coverLetterReadyBody')
    : t('opportunities.detail.atsCvReadyBody');
  const buttonLabel = isCoverLetter
    ? t('opportunities.detail.downloadCoverLetter')
    : t('opportunities.detail.downloadAtsCv');

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
      <div className="relative p-3.5">
        {/* Barre latérale - maintenant sans dégradé */}
        <div className="absolute inset-y-0 left-0 w-1 bg-neutral-300" />
        <div className="flex items-start gap-3 pl-1">
          <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-neutral-800 text-white shadow-sm">
            <Icon className="h-5 w-5" aria-hidden="true" />
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 ring-2 ring-white">
              <Sparkles className="h-2.5 w-2.5 text-white" aria-hidden="true" />
            </span>
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-neutral-900">{title}</p>
            <p className="mt-0.5 text-xs leading-5 text-neutral-500">{body}</p>
          </div>
        </div>
        <button
          type="button"
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-neutral-800 px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-neutral-700 hover:shadow-md disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-70"
          onClick={onDownload}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 bidwise-force-spin" aria-hidden="true" />
          ) : (
            <ArrowDownToLine className="h-4 w-4" aria-hidden="true" />
          )}
          <span>{loading ? t('opportunities.detail.preparingDocx') : buttonLabel}</span>
        </button>
      </div>
    </div>
  );
};

const AssistantThinkingText = () => {
  const { t } = useLanguage();
  const messages = t('opportunities.detail.assistantThinkingMessages');
  const safeMessages = Array.isArray(messages) && messages.length
    ? messages
    : [t('opportunities.detail.assistantReviewing')];
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % safeMessages.length);
    }, 1400);

    return () => window.clearInterval(timer);
  }, [safeMessages.length]);

  return (
    <span className="text-sm font-medium text-neutral-600">
      {safeMessages[index] || safeMessages[0]}
    </span>
  );
};

export const OpportunityAssistantMessages = ({
  messages = [],
  loading = false,
  error = '',
  onDownloadOptimizedCv,
  onDownloadCoverLetter,
  downloadLoadingId = '',
  threadStartRef = null,
}) => {
  const { t } = useLanguage();
  const lastUserMessageId = [...messages].reverse().find((message) => message.role === 'user')?.id || '';

  return (
    <>
      {messages.map((message) => (
        <div
          key={message.id}
          ref={message.id === lastUserMessageId ? threadStartRef : null}
          className="mt-4 scroll-mt-4"
        >
          {message.role === 'user' ? (
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2.5">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-white">{message.content}</p>
              </div>
            </div>
          ) : (
            <div className="group flex justify-start">
              <div className="relative max-w-[94%] rounded-2xl rounded-tl-md bg-white px-4 py-3 shadow-sm ring-1 ring-neutral-100">
                <div className="absolute right-1.5 top-1.5 opacity-0 transition-opacity group-hover:opacity-100">
                  <CopyMessageButton markdown={message.content} />
                </div>
                <div
                  className="prose prose-sm max-w-none pr-5 text-sm leading-relaxed prose-headings:mb-2 prose-headings:mt-3 prose-p:my-2 prose-p:text-neutral-700 prose-li:my-1 prose-li:text-neutral-700 prose-strong:text-neutral-900"
                  dangerouslySetInnerHTML={{ __html: markdownToHtml(message.content) }}
                />
                {message.action === 'optimize_cv' && onDownloadOptimizedCv ? (
                  <DownloadArtifactCard
                    variant="resume"
                    loading={downloadLoadingId === message.id}
                    onDownload={() => onDownloadOptimizedCv(message)}
                  />
                ) : null}
                {message.action === 'generate_cover_letter' && onDownloadCoverLetter ? (
                  <DownloadArtifactCard
                    variant="coverLetter"
                    loading={downloadLoadingId === message.id}
                    onDownload={() => onDownloadCoverLetter(message)}
                  />
                ) : null}
              </div>
            </div>
          )}
        </div>
      ))}

      {loading ? (
        <div className="mt-4 flex justify-start" aria-live="polite">
          <div className="rounded-2xl rounded-tl-md bg-white px-4 py-3 shadow-sm ring-1 ring-neutral-100">
            <div className="flex items-center gap-2.5">
              <AssistantRobotLoader size="sm" />
              <AssistantThinkingText />
            </div>
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="mt-4 flex gap-2 rounded-lg bg-amber-50 px-3 py-2.5 ring-1 ring-amber-100">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <p className="text-sm text-amber-700">{error}</p>
        </div>
      ) : null}
    </>
  );
};

export const OpportunityAssistantComposer = ({ loading = false, onSendQuestion }) => {
  const { t } = useLanguage();
  const [question, setQuestion] = useState('');
  const normalizedQuestion = question.trim();
  const canSend = Boolean(normalizedQuestion) && !loading;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSend) return;

    setQuestion('');
    await onSendQuestion?.(normalizedQuestion);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-neutral-100 bg-white px-4 py-3"
      aria-label={t('opportunities.detail.askAiAboutOpportunity')}
    >
      <div className="flex items-end gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 shadow-sm transition-colors focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-100">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value.slice(0, 500))}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              handleSubmit(event);
            }
          }}
          rows={1}
          maxLength={500}
          placeholder={t('opportunities.detail.askPlaceholder')}
          className="max-h-24 min-h-6 flex-1 resize-none bg-transparent text-sm leading-6 text-neutral-900 outline-none placeholder:text-neutral-400"
          aria-label={t('opportunities.detail.question')}
          aria-busy={loading}
        />
        <button
          type="submit"
          onClick={(event) => {
            if (!canSend) event.preventDefault();
          }}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md transition-colors ${
            canSend
              ? 'bg-neutral-800 text-white hover:bg-neutral-700'
              : 'bg-neutral-100 text-neutral-400'
          }`}
          aria-label={loading ? t('opportunities.detail.sendingQuestion') : t('opportunities.detail.sendQuestion')}
          title={loading ? t('opportunities.detail.sendingQuestion') : t('opportunities.detail.sendQuestion')}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      <p className="mt-1.5 text-right text-[10px] text-neutral-400">{question.length}/500</p>
    </form>
  );
};
