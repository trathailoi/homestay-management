"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { dictionaries, type Dictionary, type Locale } from "@/i18n";

interface LanguageContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  tArray: (key: string) => string[];
  dateLocale: string;
}

const STORAGE_KEY = "homestay-locale";

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

function interpolate(
  template: string,
  vars?: Record<string, string | number>
): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    vars[key] !== undefined ? String(vars[key]) : `{${key}}`
  );
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("vi");
  const [dict, setDict] = useState<Dictionary>(dictionaries.vi);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
    if (stored && (stored === "vi" || stored === "en")) {
      setLocaleState(stored);
      setDict(dictionaries[stored]);
      document.documentElement.lang = stored;
    }
  }, []);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    setDict(dictionaries[newLocale]);
    localStorage.setItem(STORAGE_KEY, newLocale);
    document.documentElement.lang = newLocale;
  }, []);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>): string => {
      const value = dict[key];
      if (typeof value === "string") return interpolate(value, vars);
      return key;
    },
    [dict]
  );

  const tArray = useCallback(
    (key: string): string[] => {
      const value = dict[key];
      if (Array.isArray(value)) return value;
      return [];
    },
    [dict]
  );

  const dateLocale = locale === "vi" ? "vi-VN" : "en-US";

  return (
    <LanguageContext.Provider value={{ locale, setLocale, t, tArray, dateLocale }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useTranslation must be used within a LanguageProvider");
  }
  return context;
}
