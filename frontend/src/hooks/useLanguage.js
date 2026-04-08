import { useMemo, useState } from "react";
import en from "../i18n/en";
import zh from "../i18n/zh";

const STORAGE_KEY = "resumematch_lang";

export function useLanguage() {
  const [lang, setLang] = useState(() => localStorage.getItem(STORAGE_KEY) || "zh");

  const toggleLanguage = () => {
    const next = lang === "zh" ? "en" : "zh";
    setLang(next);
    localStorage.setItem(STORAGE_KEY, next);
  };

  const t = useMemo(() => (lang === "zh" ? zh : en), [lang]);
  return { lang, t, toggleLanguage };
}
