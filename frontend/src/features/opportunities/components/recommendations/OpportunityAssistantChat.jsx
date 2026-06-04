import { AlertCircle, Loader2, Send } from 'lucide-react';
import { useState } from 'react';

import { CopyMessageButton, markdownToHtml } from './ResumeMatchMessageParts.jsx';

export const OpportunityAssistantMessages = ({ messages = [], loading = false, error = '' }) => (
  <>
    {messages.map((message) => (
      <div key={message.id} className="mt-4">
        {message.role === 'user' ? (
          <div className="flex justify-end">
            <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2.5">
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-white">{message.content}</p>
            </div>
          </div>
        ) : (
          <div className="group flex justify-start">
            <div className="relative max-w-[94%] rounded-2xl rounded-tl-md bg-white px-4 py-3 shadow-sm ring-1 ring-gray-100">
              <div className="absolute right-1.5 top-1.5 opacity-0 transition-opacity group-hover:opacity-100">
                <CopyMessageButton markdown={message.content} />
              </div>
              <div
                className="prose prose-sm max-w-none pr-5 text-sm leading-relaxed prose-headings:mb-2 prose-headings:mt-3 prose-p:my-2 prose-p:text-gray-700 prose-li:my-1 prose-li:text-gray-700 prose-strong:text-gray-900"
                dangerouslySetInnerHTML={{ __html: markdownToHtml(message.content) }}
              />
            </div>
          </div>
        )}
      </div>
    ))}

    {loading ? (
      <div className="mt-4 flex items-center gap-2 text-sm text-gray-500" aria-live="polite">
        <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
        <span>BidWise AI is reviewing the available details</span>
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

export const OpportunityAssistantComposer = ({ loading = false, onSendQuestion }) => {
  const [question, setQuestion] = useState('');
  const normalizedQuestion = question.trim();
  const canSend = Boolean(normalizedQuestion) && !loading;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSend) return;

    const sent = await onSendQuestion?.(normalizedQuestion);
    if (sent) {
      setQuestion('');
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-gray-100 bg-white px-4 py-3"
      aria-label="Ask BidWise AI about this opportunity"
    >
      <div className="flex items-end gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-sm transition-colors focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-100">
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
          placeholder="Ask about this opportunity..."
          className="max-h-24 min-h-6 flex-1 resize-none bg-transparent text-sm leading-6 text-gray-900 outline-none placeholder:text-gray-400"
          aria-label="Question"
          aria-busy={loading}
        />
        <button
          type="submit"
          onClick={(event) => {
            if (!canSend) event.preventDefault();
          }}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md transition-colors ${
            canSend
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-100 text-gray-400'
          }`}
          aria-label={loading ? 'Sending question' : 'Send question'}
          title={loading ? 'Sending question' : 'Send question'}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>
      <p className="mt-1.5 text-right text-[10px] text-gray-400">{question.length}/500</p>
    </form>
  );
};
