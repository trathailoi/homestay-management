"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import api, { type ApiResponse, ApiError } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import { Button } from "@/components/ui/button";
import { Media } from "@/components/guest/media";

type MediaItem = { filename: string; url: string; type: "image" | "video" };
type Scope = "hero" | "gallery" | "room";

const ACCEPT = "image/jpeg,image/png,image/webp,image/avif,video/mp4,video/webm";

function query(scope: Scope, roomNumber?: string, extra?: Record<string, string>) {
  const p = new URLSearchParams({ scope, ...extra });
  if (roomNumber) p.set("room_number", roomNumber);
  return p.toString();
}

export function MediaManager({
  scope,
  roomNumber,
}: {
  scope: Scope;
  roomNumber?: string;
}) {
  const { t } = useTranslation();
  const [items, setItems] = useState<MediaItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    const res = await api.get<ApiResponse<MediaItem[]>>(
      `/media?${query(scope, roomNumber)}`,
    );
    setItems(res.data);
  }, [scope, roomNumber]);

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [refresh]);

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.set("scope", scope);
      if (roomNumber) form.set("room_number", roomNumber);
      form.set("file", file);
      // Raw fetch: the JSON api client forces application/json, which breaks multipart.
      const res = await fetch("/api/v1/media", {
        method: "POST",
        body: form,
        credentials: "include",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error?.message ?? t("media.uploadError"));
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("media.uploadError"));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function remove(filename: string) {
    setBusy(true);
    setError(null);
    try {
      await api.delete(`/media?${query(scope, roomNumber, { filename })}`);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("media.empty")}</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {items.map((item) => (
            <div
              key={item.filename}
              className="group relative aspect-square overflow-hidden rounded-lg border bg-muted"
            >
              <Media src={item.url} className="size-full object-cover" controls={item.type === "video"} />
              <Button
                type="button"
                variant="destructive"
                size="sm"
                disabled={busy}
                onClick={() => remove(item.filename)}
                className="absolute right-1 top-1 opacity-0 transition group-hover:opacity-100"
              >
                {t("media.delete")}
              </Button>
            </div>
          ))}
        </div>
      )}

      <div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          disabled={busy}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) upload(file);
          }}
        />
        <Button type="button" disabled={busy} onClick={() => inputRef.current?.click()}>
          {busy ? t("media.uploading") : t("media.upload")}
        </Button>
      </div>
    </div>
  );
}
