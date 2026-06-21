import { Lock, MessageCircle, Sparkles, X } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useOpportunityAssistantChat } from '../../hooks/useOpportunityAssistantChat.js';
import {
  OpportunityAssistantComposer,
  OpportunityAssistantMessages,
} from './OpportunityAssistantChat.jsx';

const ACTION_SUGGESTIONS = [
  { key: 'resume_match', label: 'Is my resume a good match for this role?' },
  { key: 'optimize_cv', label: 'Optimize my CV for this role' },
  { key: 'rewrite_summary', label: 'Rewrite my professional summary' },
  { key: 'generate_cover_letter', label: 'Generate a motivation letter' },
  { key: 'interview_prep', label: 'Prepare HR interview questions' },
];

const OpportunityAssistantCard = ({
  opportunityId,
  locked = false,
  floating = false,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(!floating);
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
        aria-label={locked ? 'Sign in to ask BidWise AI' : 'Open BidWise AI assistant'}
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
            {locked ? 'Sign in to ask BidWise AI' : 'Ask BidWise AI'}
          </span>
          <span className="mt-0.5 block truncate text-xs text-gray-500">
            Skills, fit, ATS score, or application help.
          </span>
        </span>
      </button>
    );
  }

  if (locked) {
    return (
      <section className={['rounded-md border border-gray-200 bg-white p-4 shadow-sm', rootClassName].join(' ')} aria-label="BidWise AI opportunity assistant">
        {floating ? (
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="absolute right-2 top-2 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close BidWise AI"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
        <div className="flex items-start gap-3">
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-gray-100 text-gray-500">
            <Lock className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-gray-950">Sign in to ask BidWise AI</h2>
            <p className="mt-1 text-sm leading-6 text-gray-600">
              Ask questions about skills, fit, ATS score, or your application.
            </p>
            <Link
              to="/login"
              className="mt-3 inline-flex text-sm font-medium text-blue-700 hover:text-blue-800"
            >
              Sign in
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

  return (
    <section
      className={[
        'overflow-hidden rounded-md border border-gray-200 bg-white shadow-sm',
        rootClassName,
      ].join(' ')}
      aria-label="BidWise AI opportunity assistant"
    >
      <header className="border-b border-gray-100 px-4 py-3">
        <div className="flex items-center gap-2 pr-8">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-gray-950">Ask BidWise AI about this opportunity</h2>
            <p className="text-xs text-gray-500">
              Questions about skills, fit, ATS score, or your application.
            </p>
          </div>
        </div>
        {floating ? (
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="absolute right-2 top-2 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close BidWise AI"
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
          />
        ) : null}

        <div className="mt-3 space-y-2 pb-3">
          {ACTION_SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion.key}
              type="button"
              className="ml-auto flex w-fit max-w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-left text-sm font-medium text-gray-800 shadow-sm transition-colors hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-950"
              onClick={() => handleSuggestionClick(suggestion.label)}
            >
              <span>{suggestion.label}</span>
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
