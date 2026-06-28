"use client";

import Link from "next/link";
import { Waves } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";

export function GuestHeader() {
  return (
    <header className="sticky top-0 z-50 px-4 pt-3">
      <div className="mx-auto flex max-w-6xl items-center justify-between rounded-full border border-black/5 bg-white/80 px-4 py-2 shadow-lg shadow-black/5 backdrop-blur-md dark:border-white/10 dark:bg-slate-900/80">
        <Link
          href="/"
          className="flex items-center gap-2 font-display text-lg font-bold tracking-tight text-brand-blue dark:text-white"
        >
          <Waves className="size-5 text-brand" aria-hidden />
          View Biển
        </Link>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}
