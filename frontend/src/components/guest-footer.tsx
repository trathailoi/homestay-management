"use client";

import { useTranslation } from "@/lib/language-context";

export function GuestFooter() {
  const { t } = useTranslation();

  return (
    <footer className="border-t dark:border-slate-700 mt-auto">
      <div className="max-w-4xl mx-auto px-4 py-6 text-center text-sm text-slate-500 dark:text-slate-400">
        <p>{t("guest.welcome")}</p>
      </div>
    </footer>
  );
}
