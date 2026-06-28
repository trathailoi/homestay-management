"use client";

import { ExternalLink, MapPin, Phone, Star } from "lucide-react";
import { useTranslation } from "@/lib/language-context";
import { GOOGLE_MAPS_URL, MAP_EMBED_URL, reviews } from "@/lib/reviews";

// Single homestay — host contact lives here rather than in a DB/contact model.
const CONTACT_PHONE = "0355.329.669";

export function LocationReviews() {
  const { t } = useTranslation();

  return (
    <section id="location" className="mx-auto max-w-6xl px-4 py-16">
      <h2 className="font-display text-3xl font-bold tracking-tight text-brand-blue dark:text-white">
        {t("guest.locationTitle")}
      </h2>

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        <div className="overflow-hidden rounded-2xl border border-black/5 shadow-sm dark:border-white/10">
          <iframe
            src={MAP_EMBED_URL}
            title="View Biển — Google Map"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            className="aspect-[4/3] w-full"
          />
        </div>
        <div className="flex items-start gap-3">
          <MapPin className="mt-1 size-5 shrink-0 text-brand" aria-hidden />
          <div>
            <p className="font-medium">{t("guest.address")}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("guest.gettingThere")}
            </p>
            <a
              href={GOOGLE_MAPS_URL}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-indigo hover:underline"
            >
              {t("guest.openInMaps")}
              <ExternalLink className="size-3.5" aria-hidden />
            </a>
            <div className="mt-4 border-t border-black/5 pt-4 dark:border-white/10">
              <p className="font-medium">{t("guest.contactTitle")}</p>
              <a
                href={`tel:${CONTACT_PHONE.replace(/[\s.]/g, "")}`}
                className="mt-1 inline-flex items-center gap-2 text-sm font-medium text-brand-indigo hover:underline"
              >
                <Phone className="size-4" aria-hidden />
                {t("guest.contactHost")} — {CONTACT_PHONE}
              </a>
            </div>
          </div>
        </div>
      </div>

      <h3 className="mt-16 font-display text-2xl font-bold tracking-tight text-brand-blue dark:text-white">
        {t("guest.reviewsTitle")}
      </h3>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {reviews.map((review, i) => (
          <figure
            key={i}
            className="rounded-2xl border border-black/5 bg-card p-5 shadow-sm dark:border-white/10"
          >
            <div className="flex gap-0.5" aria-label={`${review.rating}/5`}>
              {Array.from({ length: 5 }).map((_, s) => (
                <Star
                  key={s}
                  className={
                    s < review.rating
                      ? "size-4 fill-amber-400 text-amber-400"
                      : "size-4 text-muted-foreground/30"
                  }
                  aria-hidden
                />
              ))}
            </div>
            <blockquote className="mt-3 text-sm text-foreground">
              {review.text}
            </blockquote>
            <figcaption className="mt-3 text-sm font-medium text-muted-foreground">
              {review.name}
            </figcaption>
          </figure>
        ))}
      </div>
      <a
        href={GOOGLE_MAPS_URL}
        target="_blank"
        rel="noreferrer"
        className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-brand-indigo hover:underline"
      >
        {t("guest.viewOnGoogle")}
        <ExternalLink className="size-3.5" aria-hidden />
      </a>
    </section>
  );
}
