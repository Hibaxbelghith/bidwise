import { useCallback, useEffect, useRef, useState } from 'react';

import { askOpportunityAssistant } from '../services/opportunitiesService.js';

const assistantErrorMessage = (error) =>
  error?.response?.data?.detail ||
  error?.response?.data?.question?.[0] ||
  error?.message ||
  'The opportunity assistant is temporarily unavailable.';

const createMessage = (role, content, metadata = {}) => ({
  id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  role,
  content,
  ...metadata,
});

export const useOpportunityAssistantChat = (opportunityId, recommendation = null) => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const requestIdRef = useRef(0);
  const isSendingRef = useRef(false);
  const messagesRef = useRef([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const reset = useCallback(() => {
    requestIdRef.current += 1;
    isSendingRef.current = false;
    setMessages([]);
    setLoading(false);
    setError('');
  }, []);

  useEffect(() => {
    reset();
  }, [opportunityId, reset]);

  const sendQuestion = useCallback(
    async (question) => {
      const normalizedQuestion = String(question || '').trim();
      if (!opportunityId || !normalizedQuestion || isSendingRef.current) {
        return false;
      }

      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      isSendingRef.current = true;
      setError('');
      setLoading(true);
      setMessages((previous) => [...previous, createMessage('user', normalizedQuestion)]);

      try {
        const history = messagesRef.current.slice(-4).map(({ role, content }) => ({ role, content }));
        const data = await askOpportunityAssistant(opportunityId, normalizedQuestion, history, recommendation);
        if (requestId !== requestIdRef.current) return false;
        const answer = String(data?.answer || '').trim();
        if (!answer) {
          throw new Error('The opportunity assistant returned an empty answer.');
        }

        setMessages((previous) => [
          ...previous,
          createMessage('assistant', answer, {
            answered: data?.answered !== false,
            source: data?.source || '',
            action: data?.action || '',
            provider: data?.provider || '',
            model: data?.model || '',
          }),
        ]);
        return true;
      } catch (requestError) {
        if (requestId !== requestIdRef.current) return false;
        setError(assistantErrorMessage(requestError));
        return false;
      } finally {
        if (requestId === requestIdRef.current) {
          isSendingRef.current = false;
          setLoading(false);
        }
      }
    },
    [opportunityId, recommendation],
  );

  return {
    messages,
    loading,
    error,
    sendQuestion,
    reset,
  };
};
