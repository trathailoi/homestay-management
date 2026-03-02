"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import api, { type ApiResponse } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import type { Room, PaginationMeta } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { CreateRoomDialog } from "@/components/create-room-dialog";

function formatCurrency(amount: string): string {
  return `$${parseFloat(amount).toFixed(2)}`;
}

export default function RoomsPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [page, setPage] = useState(1);
  const { t } = useTranslation();

  const fetchRooms = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", page.toString());
      params.set("per_page", "20");

      const response = await api.get<ApiResponse<Room[]> & { meta: PaginationMeta }>(
        `/rooms?${params.toString()}`
      );
      setRooms(response.data);
      setMeta(response.meta);
    } catch (error) {
      console.error("Failed to fetch rooms:", error);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchRooms();
  }, [fetchRooms]);

  async function handleToggleStatus(room: Room) {
    setActionLoading(room.id);
    const newStatus = room.status === "active" ? "maintenance" : "active";
    try {
      await api.patch(`/rooms/${room.id}`, { status: newStatus });
      await fetchRooms();
    } catch (error) {
      console.error("Failed to update room status:", error);
    } finally {
      setActionLoading(null);
    }
  }

  const totalPages = meta ? Math.ceil(meta.total / meta.per_page) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("rooms.title")}</h1>
        <Button onClick={() => setCreateDialogOpen(true)}>{t("rooms.addRoom")}</Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("rooms.roomNumber")}</TableHead>
              <TableHead>{t("common.name")}</TableHead>
              <TableHead>{t("common.type")}</TableHead>
              <TableHead className="text-center">{t("rooms.capacity")}</TableHead>
              <TableHead className="text-right">{t("rooms.pricePerNight")}</TableHead>
              <TableHead>{t("common.status")}</TableHead>
              <TableHead>{t("common.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  {t("common.loading")}
                </TableCell>
              </TableRow>
            ) : rooms.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  {t("rooms.noRooms")}
                </TableCell>
              </TableRow>
            ) : (
              rooms.map((room) => (
                <TableRow key={room.id}>
                  <TableCell>
                    <Link
                      href={`/rooms/${room.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {room.room_number}
                    </Link>
                  </TableCell>
                  <TableCell>{room.name}</TableCell>
                  <TableCell className="capitalize">{room.room_type}</TableCell>
                  <TableCell className="text-center">{room.max_occupancy}</TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(room.base_price_per_night)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={room.status === "active" ? "default" : "secondary"}>
                      {room.status === "active" ? t("rooms.active") : t("rooms.maintenanceStatus")}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant={room.status === "active" ? "destructive" : "default"}
                      disabled={actionLoading === room.id}
                      onClick={() => handleToggleStatus(room)}
                    >
                      {room.status === "active" ? t("rooms.lock") : t("rooms.unlock")}
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {meta && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {t("common.showing", {
              from: (page - 1) * meta.per_page + 1,
              to: Math.min(page * meta.per_page, meta.total),
              total: meta.total,
              item: t("nav.rooms").toLowerCase(),
            })}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              {t("common.previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              {t("common.next")}
            </Button>
          </div>
        </div>
      )}

      <CreateRoomDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={fetchRooms}
      />
    </div>
  );
}
