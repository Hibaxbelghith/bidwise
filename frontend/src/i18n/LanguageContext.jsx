import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import en from './translations/en.js';
import fr from './translations/fr.js';

const LANGUAGE_STORAGE_KEY = 'bidwise_language';
const DEFAULT_LANGUAGE = 'en';
const SUPPORTED_LANGUAGES = ['en', 'fr'];

const translations = { en, fr };

const LanguageContext = createContext(null);

const resolveInitialLanguage = () => {
  if (typeof window === 'undefined') return DEFAULT_LANGUAGE;
  try {
    const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return SUPPORTED_LANGUAGES.includes(storedLanguage) ? storedLanguage : DEFAULT_LANGUAGE;
  } catch {
    return DEFAULT_LANGUAGE;
  }
};

const interpolate = (text, values = {}) =>
  Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{{${key}}}`, String(value)),
    text,
  );

export const LanguageProvider = ({ children }) => {
  const [language, setLanguageState] = useState(resolveInitialLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
      // Language persistence is a convenience; the app still works without it.
    }
  }, [language]);

  const value = useMemo(() => {
    const setLanguage = (nextLanguage) => {
      if (SUPPORTED_LANGUAGES.includes(nextLanguage)) {
        setLanguageState(nextLanguage);
      }
    };

    const toggleLanguage = () => setLanguage(language === 'en' ? 'fr' : 'en');

    const t = (key, values) => {
      const segments = key.split('.');
      const text = segments.reduce((current, segment) => current?.[segment], translations[language]);
      const fallback = segments.reduce((current, segment) => current?.[segment], translations[DEFAULT_LANGUAGE]);
      return interpolate(text || fallback || key, values);
    };

    return {
      language,
      setLanguage,
      toggleLanguage,
      t,
    };
  }, [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used inside LanguageProvider');
  }
  return context;
};
