"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import api, { type ApiResponse } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
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
  const { t } = useTranslation();

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
        <p className="text-muted-foreground">{t("rooms.loadingRoom")}</p>
      </div>
    );
  }

  if (!room) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardContent className="pt-6">
            <p className="text-red-700 dark:text-red-400">{t("rooms.roomNotFound")}</p>
            <Button onClick={() => router.push("/rooms")} className="mt-4" variant="outline">
              {t("rooms.backToRooms")}
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
            &larr; {t("common.back")}
          </Button>
          <h1 className="text-2xl font-bold">{t("common.room")} {room.room_number}</h1>
          <Badge variant={room.status === "active" ? "default" : "secondary"}>
            {room.status === "active" ? t("rooms.active") : t("rooms.maintenanceStatus")}
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
            ? t("rooms.lockForMaintenance")
            : t("rooms.unlockRoom")}
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
                <p className="text-sm text-muted-foreground">{t("rooms.maxOccupancy")}</p>
                <p className="font-medium">
                  {room.max_occupancy} {room.max_occupancy === 1 ? t("common.guest") : t("common.guests")}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t("rooms.pricePerNightLabel")}</p>
                <p className="font-medium">{formatCurrency(room.base_price_per_night)}</p>
              </div>
            </div>

            {room.description && (
              <div>
                <p className="text-sm text-muted-foreground">{t("common.description")}</p>
                <p className="text-sm mt-1">{room.description}</p>
              </div>
            )}

            {room.amenities && room.amenities.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">{t("rooms.amenities")}</p>
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
            <CardTitle>{t("rooms.availabilityCalendar")}</CardTitle>
            <CardDescription>{t("rooms.clickBookedDays")}</CardDescription>
          </CardHeader>
          <CardContent>
            <RoomCalendar roomId={roomId} roomStatus={room.status} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
