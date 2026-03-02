// TypeScript interfaces matching backend response schemas

export interface Room {
  id: string;
  room_number: string;
  room_type: string;
  name: string;
  description: string | null;
  max_occupancy: number;
  base_price_per_night: string;
  amenities: string[];
  status: "active" | "maintenance";
  created_at: string;
  updated_at: string;
}

export interface AdditionalFee {
  type: "early_checkin" | "late_checkout" | "other";
  description: string;
  amount: string;
}

export interface Booking {
  id: string;
  room_id: string;
  room_number: string;
  guest_name: string;
  guest_phone: string;
  check_in_date: string;
  check_out_date: string;
  num_guests: number;
  total_amount: string;
  status: "pending" | "confirmed" | "checked_in" | "checked_out" | "cancelled";
  special_requests: string | null;
  idempotency_key: string;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  additional_fees: AdditionalFee[] | null;
  created_at: string;
  updated_at: string;
}

export interface AvailableRoom {
  id: string;
  room_number: string;
  room_type: string;
  name: string;
  max_occupancy: number;
  base_price_per_night: string;
  amenities: string[];
  total_price: string;
}

export interface RoomAvailabilityDay {
  date: string;
  is_available: boolean;
  booking_id: string | null;
}

export interface BlockingBookingInfo {
  id: string;
  guest_name: string;
  guest_phone: string;
  check_in_date: string;
  check_out_date: string;
  status: string;
}

export interface RoomAvailabilityOverview {
  id: string;
  room_number: string;
  room_type: string;
  name: string;
  max_occupancy: number;
  base_price_per_night: string;
  amenities: string[] | null;
  status: string;
  is_available: boolean;
  total_price: number | null;
  blocking_bookings: BlockingBookingInfo[];
}

export interface User {
  id: string;
  username: string;
  role: "admin" | "receptionist";
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// Request types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  role?: string;
}

export interface CreateRoomRequest {
  room_number: string;
  room_type: string;
  name: string;
  description?: string;
  max_occupancy: number;
  base_price_per_night: number;
  amenities?: string[];
  status?: "active" | "maintenance";
}

export interface UpdateRoomRequest {
  room_type?: string;
  name?: string;
  description?: string;
  max_occupancy?: number;
  base_price_per_night?: number;
  amenities?: string[];
  status?: "active" | "maintenance";
}

export interface CreateBookingRequest {
  room_id: string;
  guest_name: string;
  guest_phone: string;
  check_in_date: string;
  check_out_date: string;
  num_guests: number;
  special_requests?: string;
  idempotency_key: string;
}

export interface UpdateBookingRequest {
  special_requests?: string;
  additional_fees?: AdditionalFee[];
}

export interface CancelBookingRequest {
  reason: string;
}

// Pagination meta
export interface PaginationMeta {
  total: number;
  page: number;
  per_page: number;
}
