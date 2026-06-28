import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Prices are stored and quoted in Vietnamese đồng (VND), no decimal places.
const vndFormatter = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
})

export function formatVND(amount: number | string): string {
  return vndFormatter.format(parseFloat(String(amount)) || 0)
}
