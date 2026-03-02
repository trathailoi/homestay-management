"use client";

import { useTranslation } from "@/lib/language-context";
import { Button } from "@/components/ui/button";

export function LanguageToggle({ className }: { className?: string }) {
  const { locale, setLocale } = useTranslation();

  return (
    <Button
      variant="ghost"
      size="sm"
      className={className}
      onClick={() => setLocale(locale === "vi" ? "en" : "vi")}
    >
      {locale === "vi" ? "EN" : "VI"}
    </Button>
  );
}
