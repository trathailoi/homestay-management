"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { AvailableRoom } from "@/lib/types";

export default function GuestSearchPage() {
  const router = useRouter();
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [guests, setGuests] = useState(1);
  const [rooms, setRooms] = useState<AvailableRoom[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get today's date in YYYY-MM-DD format for min date
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
      setError("Failed to search. Please check your dates and try again.");
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
          <CardTitle>Search Available Rooms</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="check-in">Check-in Date</Label>
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
                <Label htmlFor="check-out">Check-out Date</Label>
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
                <Label htmlFor="guests">Number of Guests</Label>
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
              {loading ? "Searching..." : "Search Rooms"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-700 text-center">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {rooms !== null && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">
            {rooms.length > 0
              ? `${rooms.length} Room${rooms.length !== 1 ? "s" : ""} Available`
              : "No Rooms Available"}
          </h2>

          {rooms.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-slate-600 text-center">
                  No rooms available for these dates. Please try different dates
                  or fewer guests.
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
                        <p className="text-sm text-slate-600">
                          Room {room.room_number} &bull; Up to{" "}
                          {room.max_occupancy} guest
                          {room.max_occupancy !== 1 ? "s" : ""}
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
                      <div className="flex flex-col items-end gap-2">
                        <div className="text-right">
                          <p className="text-sm text-slate-500">
                            ${parseFloat(room.base_price_per_night).toFixed(2)}{" "}
                            / night
                          </p>
                          <p className="text-2xl font-bold text-slate-900">
                            ${parseFloat(room.total_price).toFixed(2)}
                          </p>
                          <p className="text-xs text-slate-500">total</p>
                        </div>
                        <Button onClick={() => handleRequestBooking(room.id)}>
                          Request Booking
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
