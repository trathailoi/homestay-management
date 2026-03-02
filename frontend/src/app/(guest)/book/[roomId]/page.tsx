"use client";

import { useState } from "react";
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
      <div className="max-w-md mx-auto">
        <Card className="border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950">
          <CardHeader className="text-center">
            <div className="text-4xl mb-4">&#10003;</div>
            <CardTitle className="text-green-800 dark:text-green-200">{t("guestBooking.submitted")}</CardTitle>
            <CardDescription className="text-green-700 dark:text-green-300">
              {t("guestBooking.received")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="bg-white dark:bg-slate-800 rounded-lg p-4 text-center">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">{t("guestBooking.bookingReference")}</p>
              <p className="text-2xl font-mono font-bold text-slate-900 dark:text-slate-100">
                {getBookingReference(booking.id)}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {t("guestBooking.saveReference")}
              </p>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">{t("guestBooking.checkIn")}</span>
                <span className="font-medium">{booking.check_in_date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">{t("guestBooking.checkOut")}</span>
                <span className="font-medium">{booking.check_out_date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">{t("guestBooking.guests")}</span>
                <span className="font-medium">{booking.num_guests}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">{t("guestBooking.totalAmount")}</span>
                <span className="font-medium">
                  ${parseFloat(booking.total_amount).toFixed(2)}
                </span>
              </div>
            </div>

            <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-4 text-sm text-blue-800 dark:text-blue-200">
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
    <div className="max-w-md mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>{t("guestBooking.title")}</CardTitle>
          <CardDescription>
            {t("guestBooking.subtitle")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Read-only booking details */}
            <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">{t("guestBooking.checkIn")}</span>
                <span className="font-medium">{checkIn}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">{t("guestBooking.checkOut")}</span>
                <span className="font-medium">{checkOut}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">{t("guestBooking.guests")}</span>
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
              <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-400">
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
              <Button type="submit" disabled={loading} className="flex-1">
                {loading ? t("guestBooking.submitting") : t("guestBooking.submitRequest")}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
