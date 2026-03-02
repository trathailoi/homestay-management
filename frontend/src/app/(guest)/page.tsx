"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import type { AvailableRoom } from "@/lib/types";

export default function GuestSearchPage() {
  const router = useRouter();
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [guests, setGuests] = useState(1);
  const [rooms, setRooms] = useState<AvailableRoom[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { t } = useTranslation();

  const today = new Date().toISOString().split("T")[0];

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        check_in: checkIn,
        check_out: checkOut,
        guests: guests.toString(),
      });
      const response = await api.get<{ data: AvailableRoom[] }>(
        `/availability?${params.toString()}`
      );
      setRooms(response.data);
    } catch (err) {
      console.error("Search failed:", err);
      setError(t("guest.searchFailed"));
      setRooms(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRequestBooking = (roomId: string) => {
    const params = new URLSearchParams({
      check_in: checkIn,
      check_out: checkOut,
      guests: guests.toString(),
    });
    router.push(`/book/${roomId}?${params.toString()}`);
  };

  return (
    <div className="space-y-8">
      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle>{t("guest.searchTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
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
              <div className="space-y-2">
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
              <div className="space-y-2">
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
            </div>
            <Button type="submit" disabled={loading} className="w-full md:w-auto">
              {loading ? t("guest.searching") : t("guest.searchRooms")}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardContent className="pt-6">
            <p className="text-red-700 dark:text-red-400 text-center">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {rooms !== null && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">
            {rooms.length > 0
              ? t("guest.roomsAvailable", { count: rooms.length })
              : t("guest.noRoomsAvailable")}
          </h2>

          {rooms.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-slate-600 dark:text-slate-400 text-center">
                  {t("guest.noRoomsMessage")}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {rooms.map((room) => (
                <Card key={room.id} className="overflow-hidden">
                  <CardContent className="p-6">
                    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                      <div className="space-y-2 flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold">{room.name}</h3>
                          <Badge variant="secondary">{room.room_type}</Badge>
                        </div>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          {t("common.room")} {room.room_number} &bull;{" "}
                          {t("guest.upToGuests", { count: room.max_occupancy })}
                        </p>
                        {room.amenities.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {room.amenities.map((amenity) => (
                              <Badge
                                key={amenity}
                                variant="outline"
                                className="text-xs"
                              >
                                {amenity}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-col items-start md:items-end gap-2">
                        <div className="md:text-right">
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            ${parseFloat(room.base_price_per_night).toFixed(2)}{" "}
                            {t("guest.perNight")}
                          </p>
                          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                            ${parseFloat(room.total_price).toFixed(2)}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">{t("guest.totalLabel")}</p>
                        </div>
                        <Button className="w-full md:w-auto" onClick={() => handleRequestBooking(room.id)}>
                          {t("guest.requestBooking")}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
