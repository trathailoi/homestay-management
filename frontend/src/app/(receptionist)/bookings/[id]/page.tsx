"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import api, { ApiError, type ApiResponse } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import type { Booking, AdditionalFee } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

type BookingStatus = Booking["status"];

function getStatusVariant(status: BookingStatus): "default" | "secondary" | "destructive" {
  switch (status) {
    case "confirmed":
    case "checked_in":
      return "default";
    case "cancelled":
      return "destructive";
    case "pending":
    case "checked_out":
    default:
      return "secondary";
  }
}

function formatCurrency(amount: string): string {
  return `$${parseFloat(amount).toFixed(2)}`;
}

export default function BookingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = params.id as string;
  const { t, dateLocale } = useTranslation();

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(dateLocale, {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatDateTime(dateStr: string): string {
    return new Date(dateStr).toLocaleString(dateLocale, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  const FEE_TYPES = [
    { value: "early_checkin", label: t("bookingDetail.earlyCheckin") },
    { value: "late_checkout", label: t("bookingDetail.lateCheckout") },
    { value: "other", label: t("bookingDetail.otherFee") },
  ];

  function getStatusLabel(status: BookingStatus): string {
    const map: Record<string, string> = {
      pending: t("bookings.pending"),
      confirmed: t("bookings.confirmed"),
      checked_in: t("bookings.checkedIn"),
      checked_out: t("bookings.checkedOut"),
      cancelled: t("bookings.cancelled"),
    };
    return map[status] || status;
  }

  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const [feeType, setFeeType] = useState<string>("other");
  const [feeDescription, setFeeDescription] = useState("");
  const [feeAmount, setFeeAmount] = useState("");
  const [addingFee, setAddingFee] = useState(false);

  const fetchBooking = async () => {
    try {
      const response = await api.get<ApiResponse<Booking>>(`/bookings/${bookingId}`);
      setBooking(response.data);
    } catch (error) {
      console.error("Failed to fetch booking:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBooking();
  }, [bookingId]);

  async function handleAction(action: "confirm" | "check-in" | "check-out") {
    setActionLoading(true);
    try {
      await api.post(`/bookings/${bookingId}/${action}`);
      await fetchBooking();
    } catch (error) {
      console.error(`Failed to ${action}:`, error);
      alert(error instanceof ApiError ? error.message : `Failed to ${action}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleCancel() {
    setActionLoading(true);
    try {
      await api.post(`/bookings/${bookingId}/cancel`, { reason: cancelReason || "Cancelled" });
      setCancelDialogOpen(false);
      setCancelReason("");
      await fetchBooking();
    } catch (error) {
      console.error("Failed to cancel:", error);
      alert(error instanceof ApiError ? error.message : "Failed to cancel booking");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleAddFee(e: React.FormEvent) {
    e.preventDefault();
    if (!booking || !feeDescription || !feeAmount) return;

    setAddingFee(true);
    try {
      const newFee: AdditionalFee = {
        type: feeType as "early_checkin" | "late_checkout" | "other",
        description: feeDescription,
        amount: feeAmount,
      };
      const existingFees = booking.additional_fees || [];
      await api.patch(`/bookings/${bookingId}`, {
        additional_fees: [...existingFees, newFee],
      });
      setFeeType("other");
      setFeeDescription("");
      setFeeAmount("");
      await fetchBooking();
    } catch (error) {
      console.error("Failed to add fee:", error);
      alert(error instanceof ApiError ? error.message : "Failed to add fee");
    } finally {
      setAddingFee(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-slate-500 dark:text-slate-400">{t("bookingDetail.loadingBooking")}</p>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardContent className="pt-6">
            <p className="text-red-700 dark:text-red-400">{t("bookingDetail.bookingNotFound")}</p>
            <Button onClick={() => router.push("/bookings")} className="mt-4" variant="outline">
              {t("bookingDetail.backToBookings")}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isTerminal = booking.status === "checked_out" || booking.status === "cancelled";
  const canCancel = booking.status === "pending" || booking.status === "confirmed";

  const baseFees = booking.additional_fees?.reduce(
    (sum, fee) => sum + parseFloat(fee.amount),
    0
  ) || 0;
  const totalWithFees = parseFloat(booking.total_amount) + baseFees;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2 md:gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/bookings")}>
          &larr; {t("common.back")}
        </Button>
        <h1 className="text-xl md:text-2xl font-bold">{t("bookingDetail.title")}</h1>
        <Badge variant={getStatusVariant(booking.status)} className="text-sm">
          {getStatusLabel(booking.status)}
        </Badge>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Booking Info */}
        <Card>
          <CardHeader>
            <CardTitle>{t("bookingDetail.bookingInfo")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">{t("bookingDetail.guestName")}</p>
                <p className="font-medium">{booking.guest_name}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t("bookingDetail.phone")}</p>
                <p className="font-medium">{booking.guest_phone}</p>
              </div>
            </div>

            <div>
              <p className="text-sm text-muted-foreground">{t("bookingDetail.room")}</p>
              <Link
                href={`/rooms/${booking.room_id}`}
                className="font-medium text-primary hover:underline"
              >
                {t("common.room")} {booking.room_number}
              </Link>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">{t("bookingDetail.checkIn")}</p>
                <p className="font-medium">{formatDate(booking.check_in_date)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t("bookingDetail.checkOut")}</p>
                <p className="font-medium">{formatDate(booking.check_out_date)}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">{t("bookingDetail.guestsLabel")}</p>
                <p className="font-medium">
                  {booking.num_guests} {booking.num_guests === 1 ? t("common.guest") : t("common.guests")}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t("bookingDetail.baseAmount")}</p>
                <p className="font-medium">{formatCurrency(booking.total_amount)}</p>
              </div>
            </div>

            {booking.special_requests && (
              <div>
                <p className="text-sm text-muted-foreground">{t("bookingDetail.specialRequests")}</p>
                <p className="text-sm bg-slate-50 dark:bg-slate-800 p-2 rounded mt-1">{booking.special_requests}</p>
              </div>
            )}

            {booking.status === "cancelled" && (
              <div className="border-t pt-4 mt-4">
                <p className="text-sm text-muted-foreground">{t("bookingDetail.cancellation")}</p>
                <p className="text-red-600 dark:text-red-400 font-medium">
                  {booking.cancellation_reason || t("bookingDetail.noReason")}
                </p>
                {booking.cancelled_at && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {t("bookingDetail.cancelledOn", { date: formatDateTime(booking.cancelled_at) })}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right column: Actions and Fees */}
        <div className="space-y-6">
          {!isTerminal && (
            <Card>
              <CardHeader>
                <CardTitle>{t("bookingDetail.actions")}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {booking.status === "pending" && (
                  <Button
                    disabled={actionLoading}
                    onClick={() => handleAction("confirm")}
                  >
                    {actionLoading ? "..." : t("bookingDetail.confirmBooking")}
                  </Button>
                )}

                {booking.status === "confirmed" && (
                  <Button
                    disabled={actionLoading}
                    onClick={() => handleAction("check-in")}
                  >
                    {actionLoading ? "..." : t("dashboard.checkIn")}
                  </Button>
                )}

                {booking.status === "checked_in" && (
                  <Button
                    disabled={actionLoading}
                    onClick={() => handleAction("check-out")}
                  >
                    {actionLoading ? "..." : t("dashboard.checkOut")}
                  </Button>
                )}

                {canCancel && (
                  <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
                    <DialogTrigger asChild>
                      <Button variant="destructive" disabled={actionLoading}>
                        {t("bookingDetail.cancelBooking")}
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>{t("bookingDetail.cancelConfirmTitle")}</DialogTitle>
                        <DialogDescription>
                          {t("bookingDetail.cancelConfirmDesc")}
                        </DialogDescription>
                      </DialogHeader>
                      <div className="py-4">
                        <Label htmlFor="cancel-reason">{t("bookingDetail.cancelReasonLabel")}</Label>
                        <Textarea
                          id="cancel-reason"
                          placeholder={t("bookingDetail.cancelReasonPlaceholder")}
                          value={cancelReason}
                          onChange={(e) => setCancelReason(e.target.value)}
                          className="mt-2"
                        />
                      </div>
                      <DialogFooter>
                        <Button
                          variant="outline"
                          onClick={() => setCancelDialogOpen(false)}
                        >
                          {t("bookingDetail.keepBooking")}
                        </Button>
                        <Button
                          variant="destructive"
                          disabled={actionLoading}
                          onClick={handleCancel}
                        >
                          {actionLoading ? t("bookingDetail.cancelling") : t("bookingDetail.confirmCancellation")}
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                )}
              </CardContent>
            </Card>
          )}

          {/* Additional Fees Card */}
          <Card>
            <CardHeader>
              <CardTitle>{t("bookingDetail.additionalFees")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {booking.additional_fees && booking.additional_fees.length > 0 ? (
                <div className="space-y-2">
                  {booking.additional_fees.map((fee, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-800 rounded"
                    >
                      <div>
                        <Badge variant="outline" className="mr-2">
                          {FEE_TYPES.find((ft) => ft.value === fee.type)?.label || fee.type}
                        </Badge>
                        <span className="text-sm">{fee.description}</span>
                      </div>
                      <span className="font-medium">{formatCurrency(fee.amount)}</span>
                    </div>
                  ))}
                  <div className="border-t pt-2 flex justify-between font-semibold">
                    <span>{t("bookingDetail.totalWithFees")}</span>
                    <span>{formatCurrency(totalWithFees.toFixed(2))}</span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("bookingDetail.noFees")}</p>
              )}

              {!isTerminal && (
                <form onSubmit={handleAddFee} className="border-t pt-4 space-y-3">
                  <p className="text-sm font-medium">{t("bookingDetail.addFee")}</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div>
                      <Label htmlFor="fee-type">{t("bookingDetail.feeType")}</Label>
                      <Select value={feeType} onValueChange={setFeeType}>
                        <SelectTrigger id="fee-type">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {FEE_TYPES.map((type) => (
                            <SelectItem key={type.value} value={type.value}>
                              {type.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="fee-amount">{t("bookingDetail.feeAmount")}</Label>
                      <Input
                        id="fee-amount"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="0.00"
                        value={feeAmount}
                        onChange={(e) => setFeeAmount(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="fee-description">{t("bookingDetail.feeDescription")}</Label>
                    <Input
                      id="fee-description"
                      placeholder={t("bookingDetail.feeDescriptionPlaceholder")}
                      value={feeDescription}
                      onChange={(e) => setFeeDescription(e.target.value)}
                      required
                    />
                  </div>
                  <Button type="submit" size="sm" disabled={addingFee}>
                    {addingFee ? t("bookingDetail.addingFee") : t("bookingDetail.addFee")}
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
