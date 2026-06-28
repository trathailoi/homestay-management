"use client";

import { useState } from "react";
import { formatVND } from "@/lib/utils";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import type { Booking, CreateBookingRequest } from "@/lib/types";

function generateIdempotencyKey(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

export default function BookingRequestPage() {
  const params = useParams<{ roomId: string }>();
  const searchParams = useSearchParams();
  const { t } = useTranslation();

  const roomId = params.roomId;
  const checkIn = searchParams.get("check_in") || "";
  const checkOut = searchParams.get("check_out") || "";
  const guests = parseInt(searchParams.get("guests") || "1", 10);

  const [guestName, setGuestName] = useState("");
  const [guestPhone, setGuestPhone] = useState("");
  const [specialRequests, setSpecialRequests] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const request: CreateBookingRequest = {
        room_id: roomId,
        guest_name: guestName.trim(),
        guest_phone: guestPhone.trim(),
        check_in_date: checkIn,
        check_out_date: checkOut,
        num_guests: guests,
        special_requests: specialRequests.trim() || undefined,
        idempotency_key: generateIdempotencyKey(),
      };

      const response = await api.post<{ data: Booking }>("/bookings", request);
      setBooking(response.data);
    } catch (err) {
      console.error("Booking failed:", err);
      const errorMessage =
        err instanceof Error ? err.message : t("guestBooking.submitFailed");
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getBookingReference = (id: string) => {
    return `BD-${id.substring(0, 8).toUpperCase()}`;
  };

  // Confirmation view
  if (booking) {
    return (
      <div className="mx-auto max-w-md px-4 py-12 md:py-16">
        <Card className="rounded-2xl border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950">
          <CardHeader className="text-center">
            <div className="mb-4 text-4xl">&#10003;</div>
            <CardTitle className="font-display text-green-800 dark:text-green-200">
              {t("guestBooking.submitted")}
            </CardTitle>
            <CardDescription className="text-green-700 dark:text-green-300">
              {t("guestBooking.received")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-xl bg-card p-4 text-center">
              <p className="mb-1 text-sm text-muted-foreground">
                {t("guestBooking.bookingReference")}
              </p>
              <p className="font-mono text-2xl font-bold">
                {getBookingReference(booking.id)}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {t("guestBooking.saveReference")}
              </p>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("guestBooking.checkIn")}</span>
                <span className="font-medium">{booking.check_in_date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("guestBooking.checkOut")}</span>
                <span className="font-medium">{booking.check_out_date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("guestBooking.guests")}</span>
                <span className="font-medium">{booking.num_guests}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("guestBooking.totalAmount")}</span>
                <span className="font-display font-bold text-brand-blue dark:text-white">
                  {formatVND(booking.total_amount)}
                </span>
              </div>
            </div>

            <div className="rounded-xl bg-blue-50 p-4 text-sm text-blue-800 dark:bg-blue-950 dark:text-blue-200">
              <p>{t("guestBooking.confirmMessage")}</p>
            </div>

            <Link href="/" className="block">
              <Button variant="outline" className="w-full">
                {t("guestBooking.searchMore")}
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Form view
  return (
    <div className="mx-auto max-w-md px-4 py-12 md:py-16">
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="font-display">{t("guestBooking.title")}</CardTitle>
          <CardDescription>{t("guestBooking.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Read-only booking details */}
            <div className="space-y-2 rounded-xl bg-muted p-4 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("guestBooking.checkIn")}</span>
                <span className="font-medium">{checkIn}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("guestBooking.checkOut")}</span>
                <span className="font-medium">{checkOut}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("guestBooking.guests")}</span>
                <span className="font-medium">{guests}</span>
              </div>
            </div>

            {/* Guest details form */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="guest-name">{t("guestBooking.fullName")}</Label>
                <Input
                  id="guest-name"
                  type="text"
                  value={guestName}
                  onChange={(e) => setGuestName(e.target.value)}
                  placeholder={t("guestBooking.fullNamePlaceholder")}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="guest-phone">{t("guestBooking.phone")}</Label>
                <Input
                  id="guest-phone"
                  type="tel"
                  value={guestPhone}
                  onChange={(e) => setGuestPhone(e.target.value)}
                  placeholder={t("guestBooking.phonePlaceholder")}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="special-requests">{t("guestBooking.specialRequests")}</Label>
                <Textarea
                  id="special-requests"
                  value={specialRequests}
                  onChange={(e) => setSpecialRequests(e.target.value)}
                  placeholder={t("guestBooking.specialRequestsPlaceholder")}
                  rows={3}
                />
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {/* Submit button */}
            <div className="flex gap-2">
              <Link href="/" className="flex-1">
                <Button type="button" variant="outline" className="w-full">
                  {t("guestBooking.back")}
                </Button>
              </Link>
              <Button
                type="submit"
                disabled={loading}
                className="flex-1 bg-brand text-brand-foreground hover:brightness-110"
              >
                {loading ? t("guestBooking.submitting") : t("guestBooking.submitRequest")}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
