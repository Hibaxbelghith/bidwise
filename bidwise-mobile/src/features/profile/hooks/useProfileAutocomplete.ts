import { useEffect, useMemo, useRef, useState } from 'react';

import { PROFILE_AUTOCOMPLETE_DEBOUNCE_MS } from '@/src/features/profile/constants/profileOptions';
import { suggestProfileTerms } from '@/src/features/profile/services/profileService';
import type { ProfileSuggestion, ProfileTermType } from '@/src/features/profile/types';
import { normalizeTermKey } from '@/src/features/profile/utils/profileValidation';

export function useProfileAutocomplete(termType: ProfileTermType, query: string, limit = 8) {
  const [suggestions, setSuggestions] = useState<ProfileSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const cacheRef = useRef(new Map<string, ProfileSuggestion[]>());
  const normalizedQuery = useMemo(() => normalizeTermKey(query), [query]);

  useEffect(() => {
    if (!normalizedQuery) {
      setSuggestions([]);
      setLoading(false);
      setError('');
      return undefined;
    }

    const cacheKey = `${termType}:${normalizedQuery}:${limit}`;
    const cached = cacheRef.current.get(cacheKey);
    if (cached) {
      setSuggestions(cached);
      setLoading(false);
      setError('');
      return undefined;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      setError('');
      suggestProfileTerms(termType, query.trim(), limit, controller.signal)
        .then((items) => {
          cacheRef.current.set(cacheKey, items);
          setSuggestions(items);
        })
        .catch((requestError) => {
          if (controller.signal.aborted || requestError?.code === 'ERR_CANCELED') return;
          setSuggestions([]);
          setError('Suggestions unavailable.');
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, PROFILE_AUTOCOMPLETE_DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [limit, normalizedQuery, query, termType]);

  return { suggestions, loading, error };
}
