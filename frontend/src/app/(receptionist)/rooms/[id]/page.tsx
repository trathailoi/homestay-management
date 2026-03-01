"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import api, { type ApiResponse } from "@/lib/api";
import type { Room } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RoomCalendar } from "@/components/room-calendar";

function formatCurrency(amount: string): string {
  return `$${parseFloat(amount).toFixed(2)}`;
}

export default function RoomDetailPage() {
  const params = useParams();
  const router = useRouter();
  const roomId = params.id as string;

  const [room, setRoom] = useState<Room | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchRoom = useCallback(async () => {
    try {
      const response = await api.get<ApiResponse<Room>>(`/rooms/${roomId}`);
      setRoom(response.data);
    } catch (error) {
      console.error("Failed to fetch room:", error);
    } finally {
      setLoading(false);
    }
  }, [roomId]);

  useEffect(() => {
    fetchRoom();
  }, [fetchRoom]);

  async function handleToggleStatus() {
    if (!room) return;
    setActionLoading(true);
    const newStatus = room.status === "active" ? "maintenance" : "active";
    try {
      await api.patch(`/rooms/${roomId}`, { status: newStatus });
      await fetchRoom();
    } catch (error) {
      console.error("Failed to update room status:", error);
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Loading room...</p>
      </div>
    );
  }

  if (!room) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-700">Room not found</p>
            <Button onClick={() => router.push("/rooms")} className="mt-4" variant="outline">
              Back to Rooms
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push("/rooms")}>
            &larr; Back
          </Button>
          <h1 className="text-2xl font-bold">Room {room.room_number}</h1>
          <Badge variant={room.status === "active" ? "default" : "secondary"}>
            {room.status}
          </Badge>
        </div>
        <Button
          variant={room.status === "active" ? "destructive" : "default"}
          disabled={actionLoading}
          onClick={handleToggleStatus}
        >
          {actionLoading
            ? "..."
            : room.status === "active"
            ? "Lock for Maintenance"
            : "Unlock Room"}
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Room Info */}
        <Card>
          <CardHeader>
            <CardTitle>{room.name}</CardTitle>
            <CardDescription className="capitalize">{room.room_type}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Max Occupancy</p>
                <p className="font-medium">
                  {room.max_occupancy} {room.max_occupancy === 1 ? "guest" : "guests"}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Price per Night</p>
                <p className="font-medium">{formatCurrency(room.base_price_per_night)}</p>
              </div>
            </div>

            {room.description && (
              <div>
                <p className="text-sm text-muted-foreground">Description</p>
                <p className="text-sm mt-1">{room.description}</p>
              </div>
            )}

            {room.amenities && room.amenities.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">Amenities</p>
                <div className="flex flex-wrap gap-2">
                  {room.amenities.map((amenity, index) => (
                    <Badge key={index} variant="outline">
                      {amenity}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Availability Calendar */}
        <Card>
          <CardHeader>
            <CardTitle>Availability Calendar</CardTitle>
            <CardDescription>Click on booked days to view the booking</CardDescription>
          </CardHeader>
          <CardContent>
            <RoomCalendar roomId={roomId} roomStatus={room.status} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
