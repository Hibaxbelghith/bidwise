import { Lock, MessageCircle, Sparkles, X } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import { useOpportunityAssistantChat } from '../../hooks/useOpportunityAssistantChat.js';
import { downloadCoverLetterDocx, downloadOptimizedAtsCv } from '../../services/opportunitiesService.js';
import {
  OpportunityAssistantComposer,
  OpportunityAssistantMessages,
} from './OpportunityAssistantChat.jsx';

const ACTION_SUGGESTIONS = [
  { key: 'resume_match', labelKey: 'resumeGoodMatchQuestion' },
  { key: 'optimize_cv', labelKey: 'optimizeCv' },
  { key: 'rewrite_summary', labelKey: 'rewriteMySummary' },
  { key: 'generate_cover_letter', labelKey: 'generateAMotivationLetter' },
  { key: 'interview_prep', labelKey: 'interviewPrep' },
];

const OpportunityAssistantCard = ({
  opportunityId,
  locked = false,
  floating = false,
  className = '',
}) => {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(!floating);
  const [downloadLoadingId, setDownloadLoadingId] = useState('');
  const [downloadError, setDownloadError] = useState('');
  const assistant = useOpportunityAssistantChat(opportunityId);
  const hasMessages = assistant.messages.length > 0;
  const rootClassName = floating
  ? 'fixed bottom-24 right-4 z-40 w-[min(420px,calc(100vw-2rem))] -translate-x-10 lg:bottom-6 lg:right-6 lg:-translate-x-10'
  : className;

  if (floating && !isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="fixed bottom-24 right-4 z-40 flex w-[min(340px,calc(100vw-2rem))] -translate-x-10 items-center gap-3 rounded-md border border-gray-200 bg-white px-4 py-3 text-left shadow-lg transition-all hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-blue-100 lg:bottom-6 lg:right-6 lg:-translate-x-10"
        aria-label={locked ? t('opportunities.detail.signInAskAi') : t('opportunities.detail.openBidwiseAi')}
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-700">
          {locked ? (
            <Lock className="h-5 w-5" aria-hidden="true" />
          ) : (
            <MessageCircle className="h-5 w-5" aria-hidden="true" />
          )}
        </span>
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-gray-950">
            {locked ? t('opportunities.detail.signInAskAi') : t('opportunities.detail.askBidwiseAi')}
          </span>
          <span className="mt-0.5 block truncate text-xs text-gray-500">
            {t('opportunities.detail.assistantShortHelp')}
          </span>
        </span>
      </button>
    );
  }

  if (locked) {
    return (
      <section className={['rounded-md border border-gray-200 bg-white p-4 shadow-sm', rootClassName].join(' ')} aria-label={t('opportunities.detail.askAiAboutOpportunity')}>
        {floating ? (
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="absolute right-2 top-2 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label={t('opportunities.detail.closeBidwiseAi')}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
        <div className="flex items-start gap-3">
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-gray-100 text-gray-500">
            <Lock className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-gray-950">{t('opportunities.detail.signInAskAi')}</h2>
            <p className="mt-1 text-sm leading-6 text-gray-600">
              {t('opportunities.detail.assistantHelp')}
            </p>
            <Link
              to="/login"
              className="mt-3 inline-flex text-sm font-medium text-blue-700 hover:text-blue-800"
            >
              {t('opportunities.detail.signIn')}
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const handleSuggestionClick = (label) => {
    if (assistant.loading) return;
    assistant.sendQuestion(label);
  };

  const triggerBrowserDownload = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleDownloadOptimizedCv = async (message) => {
    if (!message?.content || !opportunityId) return;

    setDownloadError('');
    setDownloadLoadingId(message.id);
    try {
      const { blob, filename } = await downloadOptimizedAtsCv(opportunityId, message.content);
      triggerBrowserDownload(blob, filename);
    } catch (requestError) {
      setDownloadError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          t('opportunities.detail.downloadDocxFailed'),
      );
    } finally {
      setDownloadLoadingId('');
    }
  };

  const handleDownloadCoverLetter = async (message) => {
    if (!message?.content || !opportunityId) return;

    setDownloadError('');
    setDownloadLoadingId(message.id);
    try {
      const { blob, filename } = await downloadCoverLetterDocx(opportunityId, message.content);
      triggerBrowserDownload(blob, filename);
    } catch (requestError) {
      setDownloadError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          t('opportunities.detail.downloadDocxFailed'),
      );
    } finally {
      setDownloadLoadingId('');
    }
  };

  return (
    <section
      className={[
        'overflow-hidden rounded-md border border-gray-200 bg-white shadow-sm',
        rootClassName,
      ].join(' ')}
      aria-label={t('opportunities.detail.askAiAboutOpportunity')}
    >
      <header className="border-b border-gray-100 px-4 py-3">
        <div className="flex items-center gap-2 pr-8">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-gray-950">{t('opportunities.detail.askAiAboutOpportunity')}</h2>
            <p className="text-xs text-gray-500">
              {t('opportunities.detail.assistantHelp')}
            </p>
          </div>
        </div>
        {floating ? (
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="absolute right-2 top-2 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label={t('opportunities.detail.closeBidwiseAi')}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </header>

      <div className="max-h-[420px] overflow-y-auto bg-gray-50 px-4 py-1">
        {hasMessages ? (
          <OpportunityAssistantMessages
            messages={assistant.messages}
            loading={assistant.loading}
            error={assistant.error}
            onDownloadOptimizedCv={handleDownloadOptimizedCv}
            onDownloadCoverLetter={handleDownloadCoverLetter}
            downloadLoadingId={downloadLoadingId}
          />
        ) : null}

        {downloadError ? (
          <div className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700 ring-1 ring-amber-100">
            {downloadError}
          </div>
        ) : null}

        <div className="mt-3 space-y-2 pb-3">
          {ACTION_SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion.key}
              type="button"
              className="ml-auto flex w-fit max-w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-left text-sm font-medium text-gray-800 shadow-sm transition-colors hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-950"
              onClick={() => handleSuggestionClick(t(`opportunities.detail.${suggestion.labelKey}`))}
            >
              <span>{t(`opportunities.detail.${suggestion.labelKey}`)}</span>
            </button>
          ))}
        </div>
      </div>

      {!hasMessages && (assistant.loading || assistant.error) ? (
        <div className="bg-gray-50 px-4 pb-3">
          <OpportunityAssistantMessages
            messages={[]}
            loading={assistant.loading}
            error={assistant.error}
          />
        </div>
      ) : null}

      <OpportunityAssistantComposer
        loading={assistant.loading}
        onSendQuestion={assistant.sendQuestion}
      />
    </section>
  );
};

export default OpportunityAssistantCard;
