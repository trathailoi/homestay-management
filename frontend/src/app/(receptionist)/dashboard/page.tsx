"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import type { Booking, Room } from "@/lib/types";

interface DashboardData {
  arrivals: Booking[];
  departures: Booking[];
  overdue: Booking[];
  pending: Booking[];
  occupiedCount: number;
  maintenanceCount: number;
  activeRoomCount: number;
}

function getToday(): string {
  return new Date().toISOString().split("T")[0];
}

function getDaysOverdue(checkOutDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const checkout = new Date(checkOutDate);
  checkout.setHours(0, 0, 0, 0);
  return Math.floor((today.getTime() - checkout.getTime()) / (1000 * 60 * 60 * 24));
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { t } = useTranslation();

  const fetchData = async () => {
    try {
      setError(null);
      const today = getToday();

      const [arrivalsRes, checkedInRes, pendingRes, roomsRes] = await Promise.all([
        api.get<{ data: Booking[] }>(
          `/bookings?status=confirmed&check_in_from=${today}&check_in_to=${today}`
        ),
        api.get<{ data: Booking[] }>("/bookings?status=checked_in"),
        api.get<{ data: Booking[] }>("/bookings?status=pending"),
        api.get<{ data: Room[] }>("/rooms"),
      ]);

      const arrivals = arrivalsRes.data;
      const checkedIn = checkedInRes.data;
      const pending = pendingRes.data;
      const rooms = roomsRes.data;

      const departures = checkedIn.filter((b) => b.check_out_date === today);
      const overdue = checkedIn.filter((b) => b.check_out_date < today);

      const activeRooms = rooms.filter((r) => r.status === "active");
      const maintenanceCount = rooms.filter((r) => r.status === "maintenance").length;
      const occupiedCount = checkedIn.length;

      setData({
        arrivals,
        departures,
        overdue,
        pending,
        occupiedCount,
        maintenanceCount,
        activeRoomCount: activeRooms.length,
      });
    } catch (err) {
      console.error("Failed to load dashboard:", err);
      setError(t("dashboard.loadError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCheckIn = async (bookingId: string) => {
    setActionLoading(bookingId);
    try {
      await api.post(`/bookings/${bookingId}/check-in`);
      await fetchData();
    } catch (err) {
      console.error("Check-in failed:", err);
      alert(err instanceof ApiError ? err.message : "Check-in failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleCheckOut = async (bookingId: string) => {
    setActionLoading(bookingId);
    try {
      await api.post(`/bookings/${bookingId}/check-out`);
      await fetchData();
    } catch (err) {
      console.error("Check-out failed:", err);
      alert(err instanceof ApiError ? err.message : "Check-out failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleConfirm = async (bookingId: string) => {
    setActionLoading(bookingId);
    try {
      await api.post(`/bookings/${bookingId}/confirm`);
      await fetchData();
    } catch (err) {
      console.error("Confirm failed:", err);
      alert(err instanceof ApiError ? err.message : "Confirm failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (bookingId: string) => {
    setActionLoading(bookingId);
    try {
      await api.post(`/bookings/${bookingId}/cancel`, {
        reason: "Rejected by receptionist",
      });
      await fetchData();
    } catch (err) {
      console.error("Reject failed:", err);
      alert(err instanceof ApiError ? err.message : "Reject failed");
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-slate-500 dark:text-slate-400">{t("dashboard.loadingDashboard")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardContent className="pt-6">
            <p className="text-red-700 dark:text-red-400">{error}</p>
            <Button onClick={fetchData} className="mt-4" variant="outline">
              {t("common.retry")}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-xl md:text-2xl font-bold">{t("dashboard.title")}</h1>

      {/* Occupancy Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">
              {t("dashboard.occupied")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {data.occupiedCount} / {data.activeRoomCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">
              {t("dashboard.maintenance")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{data.maintenanceCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">
              {t("dashboard.pendingRequests")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{data.pending.length}</p>
          </CardContent>
        </Card>
        {data.overdue.length > 0 && (
          <Card className="border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-950">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-orange-600 dark:text-orange-400">
                {t("dashboard.overdue")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-orange-700 dark:text-orange-400">
                {data.overdue.length}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Arrivals Today */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {t("dashboard.arrivalsToday")}
              <Badge variant="secondary">{data.arrivals.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.arrivals.length === 0 ? (
              <p className="text-slate-500 dark:text-slate-400 text-sm">{t("dashboard.noArrivals")}</p>
            ) : (
              <div className="space-y-3">
                {data.arrivals.map((booking) => (
                  <div
                    key={booking.id}
                    className="flex items-center justify-between p-2 md:p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
                  >
                    <div>
                      <p className="font-medium">{booking.guest_name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {t("common.room")} {booking.room_number} &bull; {booking.num_guests}{" "}
                        {booking.num_guests !== 1 ? t("common.guests") : t("common.guest")}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      disabled={actionLoading === booking.id}
                      onClick={() => handleCheckIn(booking.id)}
                    >
                      {actionLoading === booking.id ? "..." : t("dashboard.checkIn")}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Departures Today */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {t("dashboard.departuresToday")}
              <Badge variant="secondary">{data.departures.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.departures.length === 0 ? (
              <p className="text-slate-500 dark:text-slate-400 text-sm">{t("dashboard.noDepartures")}</p>
            ) : (
              <div className="space-y-3">
                {data.departures.map((booking) => (
                  <div
                    key={booking.id}
                    className="flex items-center justify-between p-2 md:p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
                  >
                    <div>
                      <p className="font-medium">{booking.guest_name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {t("common.room")} {booking.room_number}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={actionLoading === booking.id}
                      onClick={() => handleCheckOut(booking.id)}
                    >
                      {actionLoading === booking.id ? "..." : t("dashboard.checkOut")}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Overdue Check-outs */}
        {data.overdue.length > 0 && (
          <Card className="border-orange-200 dark:border-orange-800 md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-orange-700 dark:text-orange-400">
                {t("dashboard.overdueCheckouts")}
                <Badge variant="destructive">{data.overdue.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.overdue.map((booking) => (
                  <div
                    key={booking.id}
                    className="flex items-center justify-between p-2 md:p-3 bg-orange-50 dark:bg-orange-950 rounded-lg border border-orange-200 dark:border-orange-800"
                  >
                    <div>
                      <p className="font-medium">{booking.guest_name}</p>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {t("common.room")} {booking.room_number}
                      </p>
                      <Badge variant="destructive" className="mt-1">
                        {t("dashboard.daysOverdue", {
                          days: getDaysOverdue(booking.check_out_date),
                        })}
                      </Badge>
                    </div>
                    <Button
                      size="sm"
                      disabled={actionLoading === booking.id}
                      onClick={() => handleCheckOut(booking.id)}
                    >
                      {actionLoading === booking.id ? "..." : t("dashboard.checkOut")}
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Pending Requests */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {t("dashboard.pendingBookingRequests")}
              <Badge variant="secondary">{data.pending.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.pending.length === 0 ? (
              <p className="text-slate-500 dark:text-slate-400 text-sm">{t("dashboard.noPending")}</p>
            ) : (
              <div className="space-y-3">
                {data.pending.map((booking) => (
                  <div
                    key={booking.id}
                    className="flex items-center justify-between p-2 md:p-3 bg-slate-50 dark:bg-slate-800 rounded-lg gap-2"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{booking.guest_name}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {t("common.room")} {booking.room_number} &bull; {booking.check_in_date} to{" "}
                        {booking.check_out_date}
                      </p>
                      <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        ${parseFloat(booking.total_amount).toFixed(2)}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        disabled={actionLoading === booking.id}
                        onClick={() => handleConfirm(booking.id)}
                      >
                        {actionLoading === booking.id ? "..." : t("common.confirm")}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={actionLoading === booking.id}
                        onClick={() => handleReject(booking.id)}
                      >
                        {t("dashboard.reject")}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
