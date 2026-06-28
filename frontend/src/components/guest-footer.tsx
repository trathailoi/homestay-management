"use client";

import { useTranslation } from "@/lib/language-context";

export function GuestFooter() {
  const { t } = useTranslation();

  return (
    <footer className="border-t border-black/5 dark:border-white/10 mt-16">
      <div className="max-w-6xl mx-auto px-4 py-8 text-center text-sm text-muted-foreground">
        <p className="font-display font-semibold text-brand-blue dark:text-white">View Biển</p>
        <p className="mt-1">{t("guest.welcome")}</p>
      </div>
    </footer>
  );
}
