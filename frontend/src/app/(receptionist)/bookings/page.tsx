"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import api, { type ApiResponse } from "@/lib/api";
import type { Booking, PaginationMeta } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

type BookingStatus = Booking["status"];

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "checked_in", label: "Checked In" },
  { value: "checked_out", label: "Checked Out" },
  { value: "cancelled", label: "Cancelled" },
];

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
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatCurrency(amount: string): string {
  return `$${parseFloat(amount).toFixed(2)}`;
}

export default function BookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);

  const fetchBookings = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", page.toString());
      params.set("per_page", "20");
      if (statusFilter !== "all") {
        params.set("status", statusFilter);
      }
      if (searchQuery) {
        params.set("guest_search", searchQuery);
      }

      const response = await api.get<ApiResponse<Booking[]> & { meta: PaginationMeta }>(
        `/bookings?${params.toString()}`
      );
      setBookings(response.data);
      setMeta(response.meta);
    } catch (error) {
      console.error("Failed to fetch bookings:", error);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, searchQuery]);

  useEffect(() => {
    fetchBookings();
  }, [fetchBookings]);

  async function handleAction(bookingId: string, action: "confirm" | "cancel" | "check-in" | "check-out") {
    setActionLoading(bookingId);
    try {
      await api.post(`/bookings/${bookingId}/${action}`);
      await fetchBookings();
    } catch (error) {
      console.error(`Failed to ${action} booking:`, error);
    } finally {
      setActionLoading(null);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearchQuery(searchInput);
    setPage(1);
  }

  function handleStatusChange(value: string) {
    setStatusFilter(value);
    setPage(1);
  }

  const totalPages = meta ? Math.ceil(meta.total / meta.per_page) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Bookings</h1>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-md">
          <Input
            placeholder="Search by guest name or phone..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <Button type="submit" variant="secondary">
            Search
          </Button>
        </form>

        <Select value={statusFilter} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Guest</TableHead>
              <TableHead>Room</TableHead>
              <TableHead>Check-in</TableHead>
              <TableHead>Check-out</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  Loading...
                </TableCell>
              </TableRow>
            ) : bookings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No bookings found
                </TableCell>
              </TableRow>
            ) : (
              bookings.map((booking) => (
                <TableRow key={booking.id}>
                  <TableCell>
                    <Link
                      href={`/bookings/${booking.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {booking.guest_name}
                    </Link>
                    <div className="text-sm text-muted-foreground">{booking.guest_phone}</div>
                  </TableCell>
                  <TableCell>{booking.room_number}</TableCell>
                  <TableCell>{formatDate(booking.check_in_date)}</TableCell>
                  <TableCell>{formatDate(booking.check_out_date)}</TableCell>
                  <TableCell>
                    <Badge variant={getStatusVariant(booking.status)}>
                      {booking.status.replace("_", " ")}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{formatCurrency(booking.total_amount)}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {booking.status === "pending" && (
                        <>
                          <Button
                            size="sm"
                            variant="default"
                            disabled={actionLoading === booking.id}
                            onClick={() => handleAction(booking.id, "confirm")}
                          >
                            Confirm
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={actionLoading === booking.id}
                            onClick={() => handleAction(booking.id, "cancel")}
                          >
                            Reject
                          </Button>
                        </>
                      )}
                      {booking.status === "confirmed" && (
                        <Button
                          size="sm"
                          variant="default"
                          disabled={actionLoading === booking.id}
                          onClick={() => handleAction(booking.id, "check-in")}
                        >
                          Check In
                        </Button>
                      )}
                      {booking.status === "checked_in" && (
                        <Button
                          size="sm"
                          variant="default"
                          disabled={actionLoading === booking.id}
                          onClick={() => handleAction(booking.id, "check-out")}
                        >
                          Check Out
                        </Button>
                      )}
                    </div>
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
            Showing {(page - 1) * meta.per_page + 1} to{" "}
            {Math.min(page * meta.per_page, meta.total)} of {meta.total} bookings
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
