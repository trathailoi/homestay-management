"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import api, { type ApiResponse } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import type { RoomAvailabilityOverview, BlockingBookingInfo } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

function formatCurrency(amount: number | string): string {
  return `$${parseFloat(String(amount)).toFixed(2)}`;
}

function tomorrow(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split("T")[0];
}

function dayAfterTomorrow(): string {
  const d = new Date();
  d.setDate(d.getDate() + 2);
  return d.toISOString().split("T")[0];
}

export default function AvailabilityPage() {
  const [checkIn, setCheckIn] = useState(tomorrow());
  const [checkOut, setCheckOut] = useState(dayAfterTomorrow());
  const [guests, setGuests] = useState(0);
  const [rooms, setRooms] = useState<RoomAvailabilityOverview[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflictRoom, setConflictRoom] = useState<RoomAvailabilityOverview | null>(null);
  const { t } = useTranslation();

  const fetchAvailability = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        check_in: checkIn,
        check_out: checkOut,
        guests: guests.toString(),
      });
      const response = await api.get<ApiResponse<RoomAvailabilityOverview[]>>(
        `/availability/overview?${params.toString()}`
      );
      setRooms(response.data);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  }, [checkIn, checkOut, guests, t]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (checkIn >= checkOut) {
      setError(t("availability.checkOutAfterCheckIn"));
      return;
    }
    fetchAvailability();
  }

  const numNights = Math.max(
    0,
    Math.floor(
      (new Date(checkOut).getTime() - new Date(checkIn).getTime()) /
        (1000 * 60 * 60 * 24)
    )
  );

  return (
    <div className="space-y-6">
      <h1 className="text-xl md:text-2xl font-bold">{t("availability.title")}</h1>

      <form onSubmit={handleSearch} className="flex flex-wrap items-end gap-4">
        <div className="w-full md:w-auto space-y-1">
          <Label htmlFor="check-in">{t("availability.checkIn")}</Label>
          <Input
            id="check-in"
            type="date"
            value={checkIn}
            onChange={(e) => setCheckIn(e.target.value)}
            required
          />
        </div>
        <div className="w-full md:w-auto space-y-1">
          <Label htmlFor="check-out">{t("availability.checkOut")}</Label>
          <Input
            id="check-out"
            type="date"
            value={checkOut}
            onChange={(e) => setCheckOut(e.target.value)}
            required
          />
        </div>
        <div className="w-full md:w-auto space-y-1">
          <Label htmlFor="guests">{t("availability.minGuests")}</Label>
          <Input
            id="guests"
            type="number"
            min={0}
            value={guests}
            onChange={(e) => setGuests(parseInt(e.target.value) || 0)}
            className="md:w-24"
          />
        </div>
        <Button type="submit" disabled={loading} className="w-full md:w-auto">
          {loading ? t("availability.searching") : t("common.search")}
        </Button>
      </form>

      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-md px-4 py-2">
          {error}
        </div>
      )}

      {searched && !loading && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {t("availability.roomsFound", { count: rooms.length })}
            {numNights > 0 && ` ${t("availability.forNights", { nights: numNights })}`}
          </p>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {rooms.map((room) => (
              <Card
                key={room.id}
                className={
                  room.is_available
                    ? "border-green-300 bg-green-50/50 dark:border-green-700 dark:bg-green-950/50"
                    : "opacity-60 border-gray-300 dark:border-gray-700"
                }
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">
                      <Link
                        href={`/rooms/${room.id}`}
                        className="hover:underline"
                      >
                        {room.room_number} &mdash; {room.name}
                      </Link>
                    </CardTitle>
                    {room.is_available ? (
                      <Badge variant="default" className="bg-green-600">
                        {t("availability.available")}
                      </Badge>
                    ) : room.status === "maintenance" ? (
                      <Badge variant="secondary">{t("dashboard.maintenance")}</Badge>
                    ) : (
                      <Badge variant="destructive">{t("availability.unavailable")}</Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span className="capitalize">{room.room_type}</span>
                    <span>{t("availability.upToGuests", { count: room.max_occupancy })}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>{formatCurrency(room.base_price_per_night)}{t("common.perNight")}</span>
                    {room.is_available && room.total_price !== null && (
                      <span className="font-semibold text-green-700 dark:text-green-400">
                        {t("common.total")}: {formatCurrency(room.total_price)}
                      </span>
                    )}
                  </div>
                  {room.amenities && room.amenities.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {room.amenities.map((a) => (
                        <Badge key={a} variant="outline" className="text-xs">
                          {a}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {!room.is_available && room.blocking_bookings.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full mt-2"
                      onClick={() => setConflictRoom(room)}
                    >
                      {t("availability.viewConflicts", { count: room.blocking_bookings.length })}
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      <Dialog
        open={conflictRoom !== null}
        onOpenChange={(open) => {
          if (!open) setConflictRoom(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t("availability.blockingBookings", { room: conflictRoom?.room_number || "" })}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {conflictRoom?.blocking_bookings.map(
              (booking: BlockingBookingInfo) => (
                <div
                  key={booking.id}
                  className="border rounded-md p-3 space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{booking.guest_name}</span>
                    <Badge variant="outline" className="capitalize">
                      {booking.status}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {booking.guest_phone}
                  </div>
                  <div className="text-sm">
                    {booking.check_in_date} &rarr; {booking.check_out_date}
                  </div>
                  <Link
                    href={`/bookings/${booking.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    {t("availability.viewBooking")}
                  </Link>
                </div>
              )
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
