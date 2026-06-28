"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { useTranslation } from "@/lib/language-context";

export function Gallery({ photos }: { photos: string[] }) {
  const { t } = useTranslation();
  const [active, setActive] = useState<string | null>(null);

  return (
    <section id="gallery" className="mx-auto max-w-6xl px-4 py-16">
      <h2 className="font-display text-3xl font-bold tracking-tight text-brand-blue dark:text-white">
        {t("guest.galleryTitle")}
      </h2>
      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        {photos.map((src, i) => (
          <button
            key={`${src}-${i}`}
            onClick={() => setActive(src)}
            className="group relative aspect-square overflow-hidden rounded-2xl bg-muted"
            aria-label={t("guest.galleryTitle")}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- dynamic public photo */}
            <img
              src={src}
              alt=""
              className="size-full object-cover transition duration-300 group-hover:scale-105"
            />
          </button>
        ))}
      </div>

      <Dialog open={!!active} onOpenChange={(open) => !open && setActive(null)}>
        <DialogContent className="max-w-4xl border-0 bg-transparent p-0 shadow-none">
          <DialogTitle className="sr-only">{t("guest.galleryTitle")}</DialogTitle>
          {active && (
            // eslint-disable-next-line @next/next/no-img-element -- dynamic public photo
            <img src={active} alt="" className="max-h-[85vh] w-full rounded-2xl object-contain" />
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}
