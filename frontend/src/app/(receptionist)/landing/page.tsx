"use client";

import { useTranslation } from "@/lib/language-context";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { MediaManager } from "@/components/admin/MediaManager";

export default function LandingMediaPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <h1 className="text-xl md:text-2xl font-bold">{t("landing.title")}</h1>

      <Card>
        <CardHeader>
          <CardTitle>{t("landing.heroTitle")}</CardTitle>
          <CardDescription>{t("landing.heroHint")}</CardDescription>
        </CardHeader>
        <CardContent>
          <MediaManager scope="hero" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("landing.galleryTitle")}</CardTitle>
          <CardDescription>{t("landing.galleryHint")}</CardDescription>
        </CardHeader>
        <CardContent>
          <MediaManager scope="gallery" />
        </CardContent>
      </Card>
    </div>
  );
}
