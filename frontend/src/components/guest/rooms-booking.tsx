"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import type { AvailableRoom, Room } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Mirrors photos.ts PLACEHOLDER (that module is server-only; can't import here).
const PLACEHOLDER = "/photos/placeholder.svg";

type Props = { roomPhotos: Record<string, string[]> };

export function RoomsBooking({ roomPhotos }: Props) {
  const router = useRouter();
  const { t } = useTranslation();
  const today = new Date().toISOString().split("T")[0];

  const [rooms, setRooms] = useState<Room[] | null>(null);
  const [loadError, setLoadError] = useState(false);

  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [guests, setGuests] = useState(1);
  const [available, setAvailable] = useState<AvailableRoom[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const loadRooms = useCallback(async () => {
    setLoadError(false);
    try {
      const res = await api.get<{ data: Room[] }>(
        "/rooms?status=active&per_page=100",
      );
      setRooms(res.data);
    } catch (err) {
      console.error("Failed to load rooms:", err);
      setLoadError(true);
    }
  }, []);

  useEffect(() => {
    loadRooms();
  }, [loadRooms]);

  const photoFor = (roomNumber: string) =>
    roomPhotos[roomNumber]?.[0] ?? PLACEHOLDER;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setSearching(true);
    setSearchError(null);
    try {
      const params = new URLSearchParams({
        check_in: checkIn,
        check_out: checkOut,
        guests: String(guests),
      });
      const res = await api.get<{ data: AvailableRoom[] }>(
        `/availability?${params.toString()}`,
      );
      setAvailable(res.data);
    } catch (err) {
      console.error("Search failed:", err);
      setSearchError(t("guest.searchFailed"));
      setAvailable(null);
    } finally {
      setSearching(false);
    }
  };

  const clearDates = () => {
    setAvailable(null);
    setSearchError(null);
  };

  const book = (roomId: string) => {
    const params = new URLSearchParams({
      check_in: checkIn,
      check_out: checkOut,
      guests: String(guests),
    });
    router.push(`/book/${roomId}?${params.toString()}`);
  };

  return (
    <section id="rooms" className="mx-auto max-w-6xl px-4 py-16">
      <h2 className="font-display text-3xl font-bold tracking-tight text-brand-blue dark:text-white">
        {t("guest.roomsTitle")}
      </h2>
      <p className="mt-2 text-muted-foreground">{t("guest.roomsIntro")}</p>

      {/* Date + guests bar */}
      <form
        onSubmit={handleSearch}
        className="mt-6 grid grid-cols-1 gap-3 rounded-2xl border border-black/5 bg-card p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4 dark:border-white/10"
      >
        <div className="space-y-1.5">
          <Label htmlFor="check-in">{t("guest.checkInDate")}</Label>
          <Input
            id="check-in"
            type="date"
            min={today}
            value={checkIn}
            onChange={(e) => setCheckIn(e.target.value)}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="check-out">{t("guest.checkOutDate")}</Label>
          <Input
            id="check-out"
            type="date"
            min={checkIn || today}
            value={checkOut}
            onChange={(e) => setCheckOut(e.target.value)}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="guests">{t("guest.numberOfGuests")}</Label>
          <Input
            id="guests"
            type="number"
            min={1}
            max={10}
            value={guests}
            onChange={(e) => setGuests(parseInt(e.target.value) || 1)}
            required
          />
        </div>
        <div className="flex items-end gap-2">
          <Button type="submit" disabled={searching} className="flex-1">
            {searching ? t("guest.searching") : t("guest.checkAvailability")}
          </Button>
          {available !== null && (
            <Button type="button" variant="ghost" onClick={clearDates}>
              {t("guest.clearDates")}
            </Button>
          )}
        </div>
      </form>

      {searchError && (
        <p className="mt-4 rounded-xl bg-destructive/10 px-4 py-3 text-center text-sm text-destructive">
          {searchError}
        </p>
      )}

      {/* Listing */}
      <div className="mt-8">
        {loadError ? (
          <div className="rounded-2xl border border-black/5 bg-card p-8 text-center dark:border-white/10">
            <p className="text-muted-foreground">{t("guest.loadFailed")}</p>
            <Button onClick={loadRooms} variant="outline" className="mt-4">
              {t("guest.retry")}
            </Button>
          </div>
        ) : rooms === null ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-80 animate-pulse rounded-2xl bg-muted"
              />
            ))}
          </div>
        ) : available !== null ? (
          available.length === 0 ? (
            <EmptyState message={t("guest.noRoomsMessage")} />
          ) : (
            <>
              <h3 className="mb-4 text-lg font-semibold">
                {t("guest.roomsAvailable", { count: available.length })}
              </h3>
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {available.map((room) => (
                  <RoomCard
                    key={room.id}
                    photo={photoFor(room.room_number)}
                    name={room.name}
                    roomType={room.room_type}
                    roomNumber={room.room_number}
                    maxOccupancy={room.max_occupancy}
                    amenities={room.amenities}
                    pricePerNight={room.base_price_per_night}
                    totalPrice={room.total_price}
                    perNightLabel={t("guest.perNight")}
                    totalLabel={t("guest.totalLabel")}
                    roomLabel={t("common.room")}
                    upToLabel={t("guest.upToGuests", { count: room.max_occupancy })}
                    action={
                      <Button
                        className="w-full bg-brand text-brand-foreground hover:brightness-110"
                        onClick={() => book(room.id)}
                      >
                        {t("guest.requestBooking")}
                      </Button>
                    }
                  />
                ))}
              </div>
            </>
          )
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {rooms.map((room) => (
              <RoomCard
                key={room.id}
                photo={photoFor(room.room_number)}
                name={room.name}
                roomType={room.room_type}
                roomNumber={room.room_number}
                maxOccupancy={room.max_occupancy}
                amenities={room.amenities}
                description={room.description}
                pricePerNight={room.base_price_per_night}
                perNightLabel={t("guest.perNight")}
                fromLabel={t("guest.fromPrice")}
                roomLabel={t("common.room")}
                upToLabel={t("guest.upToGuests", { count: room.max_occupancy })}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-black/5 bg-card p-8 text-center text-muted-foreground dark:border-white/10">
      {message}
    </div>
  );
}

type RoomCardProps = {
  photo: string;
  name: string;
  roomType: string;
  roomNumber: string;
  maxOccupancy: number;
  amenities: string[] | null;
  description?: string | null;
  pricePerNight: string;
  totalPrice?: string;
  perNightLabel: string;
  totalLabel?: string;
  fromLabel?: string;
  roomLabel: string;
  upToLabel: string;
  action?: React.ReactNode;
};

function RoomCard({
  photo,
  name,
  roomType,
  roomNumber,
  amenities,
  description,
  pricePerNight,
  totalPrice,
  perNightLabel,
  totalLabel,
  fromLabel,
  roomLabel,
  upToLabel,
  action,
}: RoomCardProps) {
  return (
    <div className="flex flex-col overflow-hidden rounded-2xl border border-black/5 bg-card shadow-sm transition hover:shadow-md dark:border-white/10">
      <div className="relative aspect-[16/10] overflow-hidden bg-muted">
        {/* eslint-disable-next-line @next/next/no-img-element -- dynamic public photo */}
        <img src={photo} alt={name} className="size-full object-cover" />
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-display text-lg font-semibold">{name}</h3>
          <Badge variant="secondary">{roomType}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          {roomLabel} {roomNumber} &bull; {upToLabel}
        </p>
        {description && (
          <p className="line-clamp-2 text-sm text-muted-foreground">{description}</p>
        )}
        {amenities && amenities.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {amenities.slice(0, 4).map((a) => (
              <Badge key={a} variant="outline" className="text-xs font-normal">
                {a}
              </Badge>
            ))}
          </div>
        )}
        <div className="mt-auto flex items-end justify-between pt-2">
          <div>
            {totalPrice ? (
              <>
                <p className="font-display text-xl font-bold">
                  ${parseFloat(totalPrice).toFixed(2)}
                </p>
                <p className="text-xs text-muted-foreground">{totalLabel}</p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                {fromLabel}{" "}
                <span className="font-display text-xl font-bold text-foreground">
                  ${parseFloat(pricePerNight).toFixed(2)}
                </span>{" "}
                {perNightLabel}
              </p>
            )}
          </div>
        </div>
        {action}
      </div>
    </div>
  );
}
