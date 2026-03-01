"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import api, { type ApiResponse } from "@/lib/api";
import type { AdditionalFee, Booking } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatCurrency(amount: string): string {
  return `$${parseFloat(amount).toFixed(2)}`;
}

const FEE_TYPE_LABELS: Record<AdditionalFee["type"], string> = {
  early_checkin: "Early Check-in",
  late_checkout: "Late Checkout",
  other: "Other",
};

export default function BookingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const bookingId = params.id as string;

  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Cancel dialog state
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  // Add fee form state
  const [feeType, setFeeType] = useState<AdditionalFee["type"]>("other");
  const [feeDescription, setFeeDescription] = useState("");
  const [feeAmount, setFeeAmount] = useState("");
  const [feeLoading, setFeeLoading] = useState(false);

  const fetchBooking = useCallback(async () => {
    try {
      const response = await api.get<ApiResponse<Booking>>(`/bookings/${bookingId}`);
      setBooking(response.data);
    } catch (error) {
      console.error("Failed to fetch booking:", error);
    } finally {
      setLoading(false);
    }
  }, [bookingId]);

  useEffect(() => {
    fetchBooking();
  }, [fetchBooking]);

  async function handleAction(action: "confirm" | "check-in" | "check-out") {
    setActionLoading(true);
    try {
      await api.post(`/bookings/${bookingId}/${action}`);
      await fetchBooking();
    } catch (error) {
      console.error(`Failed to ${action} booking:`, error);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleCancel() {
    setActionLoading(true);
    try {
      await api.post(`/bookings/${bookingId}/cancel`, { reason: cancelReason || undefined });
      setCancelDialogOpen(false);
      setCancelReason("");
      await fetchBooking();
    } catch (error) {
      console.error("Failed to cancel booking:", error);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleAddFee(e: React.FormEvent) {
    e.preventDefault();
    if (!booking) return;

    setFeeLoading(true);
    try {
      const existingFees = booking.additional_fees || [];
      const newFee: AdditionalFee = {
        type: feeType,
        description: feeDescription,
        amount: feeAmount,
      };
      const updatedFees = [...existingFees, newFee];

      await api.patch(`/bookings/${bookingId}`, { additional_fees: updatedFees });
      setFeeType("other");
      setFeeDescription("");
      setFeeAmount("");
      await fetchBooking();
    } catch (error) {
      console.error("Failed to add fee:", error);
    } finally {
      setFeeLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Booking not found</div>
      </div>
    );
  }

  const isTerminal = booking.status === "checked_out" || booking.status === "cancelled";
  const canCancel = booking.status === "pending" || booking.status === "confirmed";

  // Calculate total with fees
  const baseFees = booking.additional_fees || [];
  const totalFees = baseFees.reduce((sum, fee) => sum + parseFloat(fee.amount), 0);
  const grandTotal = parseFloat(booking.total_amount) + totalFees;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.back()}>
            &larr; Back
          </Button>
          <h1 className="text-2xl font-bold">Booking Details</h1>
          <Badge variant={getStatusVariant(booking.status)}>
            {booking.status.replace("_", " ")}
          </Badge>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Left Column: Booking Info */}
        <Card>
          <CardHeader>
            <CardTitle>Booking Information</CardTitle>
            <CardDescription>Guest and reservation details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Guest Name</div>
                <div className="font-medium">{booking.guest_name}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Phone</div>
                <div className="font-medium">{booking.guest_phone}</div>
              </div>
            </div>

            <div>
              <div className="text-sm text-muted-foreground">Room</div>
              <Link
                href={`/rooms/${booking.room_id}`}
                className="font-medium text-primary hover:underline"
              >
                Room {booking.room_number}
              </Link>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Check-in</div>
                <div className="font-medium">{formatDate(booking.check_in_date)}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Check-out</div>
                <div className="font-medium">{formatDate(booking.check_out_date)}</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Number of Guests</div>
                <div className="font-medium">{booking.num_guests}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Base Amount</div>
                <div className="font-medium">{formatCurrency(booking.total_amount)}</div>
              </div>
            </div>

            {booking.special_requests && (
              <div>
                <div className="text-sm text-muted-foreground">Special Requests</div>
                <div className="mt-1 text-sm bg-slate-50 p-3 rounded-md">
                  {booking.special_requests}
                </div>
              </div>
            )}

            {booking.status === "cancelled" && booking.cancelled_at && (
              <div className="border-t pt-4 mt-4">
                <div className="text-sm font-medium text-destructive">Cancellation Info</div>
                <div className="text-sm text-muted-foreground mt-1">
                  Cancelled on {formatDateTime(booking.cancelled_at)}
                </div>
                {booking.cancellation_reason && (
                  <div className="mt-2 text-sm bg-red-50 p-3 rounded-md text-red-700">
                    {booking.cancellation_reason}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right Column: Actions + Fees */}
        <div className="space-y-6">
          {/* Actions Card */}
          {!isTerminal && (
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
                <CardDescription>Update booking status</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {booking.status === "pending" && (
                  <Button
                    onClick={() => handleAction("confirm")}
                    disabled={actionLoading}
                  >
                    Confirm Booking
                  </Button>
                )}
                {booking.status === "confirmed" && (
                  <Button
                    onClick={() => handleAction("check-in")}
                    disabled={actionLoading}
                  >
                    Check In Guest
                  </Button>
                )}
                {booking.status === "checked_in" && (
                  <Button
                    onClick={() => handleAction("check-out")}
                    disabled={actionLoading}
                  >
                    Check Out Guest
                  </Button>
                )}
                {canCancel && (
                  <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
                    <DialogTrigger asChild>
                      <Button variant="destructive">Cancel Booking</Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Cancel Booking</DialogTitle>
                        <DialogDescription>
                          Are you sure you want to cancel this booking? This action cannot be undone.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-2">
                        <Label htmlFor="cancelReason">Reason (optional)</Label>
                        <Textarea
                          id="cancelReason"
                          value={cancelReason}
                          onChange={(e) => setCancelReason(e.target.value)}
                          placeholder="Enter cancellation reason..."
                          rows={3}
                        />
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>
                          Keep Booking
                        </Button>
                        <Button
                          variant="destructive"
                          onClick={handleCancel}
                          disabled={actionLoading}
                        >
                          Confirm Cancellation
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
              <CardTitle>Additional Fees</CardTitle>
              <CardDescription>Extra charges for this booking</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Existing fees list */}
              {baseFees.length > 0 ? (
                <div className="space-y-2">
                  {baseFees.map((fee, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-2 border-b last:border-0"
                    >
                      <div>
                        <div className="font-medium text-sm">
                          {FEE_TYPE_LABELS[fee.type]}
                        </div>
                        <div className="text-sm text-muted-foreground">{fee.description}</div>
                      </div>
                      <div className="font-medium">{formatCurrency(fee.amount)}</div>
                    </div>
                  ))}
                  <div className="flex items-center justify-between pt-2 border-t font-medium">
                    <div>Total with Fees</div>
                    <div>{formatCurrency(grandTotal.toString())}</div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">No additional fees</div>
              )}

              {/* Add fee form */}
              {!isTerminal && (
                <form onSubmit={handleAddFee} className="space-y-3 pt-4 border-t">
                  <div className="text-sm font-medium">Add New Fee</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label htmlFor="feeType">Type</Label>
                      <Select
                        value={feeType}
                        onValueChange={(v) => setFeeType(v as AdditionalFee["type"])}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="early_checkin">Early Check-in</SelectItem>
                          <SelectItem value="late_checkout">Late Checkout</SelectItem>
                          <SelectItem value="other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="feeAmount">Amount ($)</Label>
                      <Input
                        id="feeAmount"
                        type="number"
                        min="0"
                        step="0.01"
                        value={feeAmount}
                        onChange={(e) => setFeeAmount(e.target.value)}
                        placeholder="0.00"
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="feeDescription">Description</Label>
                    <Input
                      id="feeDescription"
                      value={feeDescription}
                      onChange={(e) => setFeeDescription(e.target.value)}
                      placeholder="e.g., Early check-in at 10am"
                      required
                    />
                  </div>
                  <Button type="submit" size="sm" disabled={feeLoading}>
                    {feeLoading ? "Adding..." : "Add Fee"}
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
