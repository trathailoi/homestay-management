"use client";

import { useTranslation } from "@/lib/language-context";
import { Media } from "@/components/guest/media";

export function Hero({ photo }: { photo: string }) {
  const { t } = useTranslation();

  return (
    <section className="relative h-[80vh] min-h-[480px] w-full overflow-hidden">
      <Media
        src={photo}
        alt="View Biển"
        className="absolute inset-0 size-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/15 to-black/65" />
      <div className="relative z-10 flex h-full flex-col items-center justify-center px-4 text-center text-white">
        <h1 className="font-display text-4xl font-bold tracking-tight drop-shadow-lg sm:text-6xl">
          View Biển
        </h1>
        <p className="mt-4 max-w-xl text-lg text-white/90 drop-shadow sm:text-xl">
          {t("guest.heroTagline")}
        </p>
        <a
          href="#rooms"
          className="mt-8 inline-flex items-center rounded-full bg-brand px-8 py-3 font-semibold text-brand-foreground shadow-lg shadow-black/20 transition hover:brightness-110"
        >
          {t("guest.bookNow")}
        </a>
      </div>
    </section>
  );
}
