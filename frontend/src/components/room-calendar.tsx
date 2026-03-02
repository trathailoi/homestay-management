"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api, { type ApiResponse } from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import type { RoomAvailabilityDay } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RoomCalendarProps {
  roomId: string;
  roomStatus: "active" | "maintenance";
}

function formatDateKey(date: Date): string {
  return date.toISOString().split("T")[0];
}

function getDaysInMonth(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
}

function getFirstDayOfMonth(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
}

export function RoomCalendar({ roomId, roomStatus }: RoomCalendarProps) {
  const router = useRouter();
  const { t, tArray, dateLocale } = useTranslation();
  const [currentMonth, setCurrentMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const [availability, setAvailability] = useState<Map<string, RoomAvailabilityDay>>(new Map());
  const [loading, setLoading] = useState(true);

  const weekdays = tArray("calendar.weekdays");

  function formatMonthYear(date: Date): string {
    return date.toLocaleDateString(dateLocale, { month: "long", year: "numeric" });
  }

  const fetchAvailability = useCallback(async () => {
    setLoading(true);
    try {
      const startDate = formatDateKey(currentMonth);
      const endDate = formatDateKey(
        new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0)
      );

      const response = await api.get<ApiResponse<RoomAvailabilityDay[]>>(
        `/availability/rooms/${roomId}?start_date=${startDate}&end_date=${endDate}`
      );

      const dayMap = new Map<string, RoomAvailabilityDay>();
      response.data.forEach((day) => {
        dayMap.set(day.date, day);
      });
      setAvailability(dayMap);
    } catch (error) {
      console.error("Failed to fetch availability:", error);
    } finally {
      setLoading(false);
    }
  }, [roomId, currentMonth]);

  useEffect(() => {
    fetchAvailability();
  }, [fetchAvailability]);

  function handlePrevMonth() {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
  }

  function handleNextMonth() {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
  }

  function handleDayClick(day: RoomAvailabilityDay) {
    if (day.booking_id) {
      router.push(`/bookings/${day.booking_id}`);
    }
  }

  const daysInMonth = getDaysInMonth(currentMonth);
  const firstDayOfWeek = getFirstDayOfMonth(currentMonth);

  const days: (number | null)[] = [];
  for (let i = 0; i < firstDayOfWeek; i++) {
    days.push(null);
  }
  for (let i = 1; i <= daysInMonth; i++) {
    days.push(i);
  }

  return (
    <div className="space-y-4">
      {/* Month navigation */}
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={handlePrevMonth}>
          &larr; {t("calendar.prev")}
        </Button>
        <h3 className="text-lg font-semibold">{formatMonthYear(currentMonth)}</h3>
        <Button variant="outline" size="sm" onClick={handleNextMonth}>
          {t("calendar.next")} &rarr;
        </Button>
      </div>

      {/* Calendar grid */}
      {loading ? (
        <div className="text-center py-8 text-muted-foreground">{t("common.loading")}</div>
      ) : (
        <>
          {/* Weekday headers */}
          <div className="grid grid-cols-7 gap-1 text-center text-sm text-muted-foreground">
            {weekdays.map((day) => (
              <div key={day} className="py-2 font-medium">
                {day}
              </div>
            ))}
          </div>

          {/* Day cells */}
          <div className="grid grid-cols-7 gap-1">
            {days.map((dayNum, index) => {
              if (dayNum === null) {
                return <div key={`empty-${index}`} className="aspect-square" />;
              }

              const dateKey = formatDateKey(
                new Date(currentMonth.getFullYear(), currentMonth.getMonth(), dayNum)
              );
              const dayData = availability.get(dateKey);

              let bgColor = "bg-slate-100 dark:bg-slate-800";
              let textColor = "text-slate-400 dark:text-slate-500";
              let cursor = "cursor-default";
              let hoverEffect = "";

              if (roomStatus === "maintenance") {
                bgColor = "bg-slate-300 dark:bg-slate-700";
                textColor = "text-slate-500 dark:text-slate-400";
              } else if (dayData) {
                if (dayData.is_available) {
                  bgColor = "bg-green-100 dark:bg-green-900";
                  textColor = "text-green-800 dark:text-green-200";
                } else {
                  bgColor = "bg-red-100 dark:bg-red-900";
                  textColor = "text-red-800 dark:text-red-200";
                  cursor = "cursor-pointer";
                  hoverEffect = "hover:bg-red-200 dark:hover:bg-red-800";
                }
              }

              return (
                <div
                  key={dateKey}
                  className={cn(
                    "aspect-square flex items-center justify-center rounded-md text-sm font-medium",
                    bgColor,
                    textColor,
                    cursor,
                    hoverEffect
                  )}
                  onClick={() => dayData && handleDayClick(dayData)}
                  title={
                    dayData?.booking_id
                      ? t("calendar.clickToViewBooking")
                      : dayData?.is_available
                      ? t("calendar.available")
                      : roomStatus === "maintenance"
                      ? t("calendar.roomInMaintenance")
                      : ""
                  }
                >
                  {dayNum}
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-4 text-sm pt-2 border-t dark:border-slate-700">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-green-100 dark:bg-green-900 border border-green-200 dark:border-green-700" />
              <span>{t("calendar.available")}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-red-100 dark:bg-red-900 border border-red-200 dark:border-red-700" />
              <span>{t("calendar.booked")}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-slate-300 dark:bg-slate-700 border border-slate-400 dark:border-slate-600" />
              <span>{t("calendar.maintenance")}</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
