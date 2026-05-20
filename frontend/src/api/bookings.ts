/** Shared booking types and constants used by client and master API modules. */

export type PaginatedBookings = {
  items: Booking[]
  total: number
  page: number
  page_size: number
}

export type Booking = {
  id: string
  master_id: string
  client_id: string
  service_id: string
  start_at: string
  end_at: string
  duration_min: number
  price_snapshot: string
  currency_snapshot: string
  status: string
  attendance_confirmed_at?: string | null
  cancel_comment?: string | null
  reschedule_comment?: string | null
}

export const BOOKING_COMMENT_MAX_LENGTH = 500

export type BookingClientListItem = Booking & {
  master_display_name: string
  service_name: string
}

export type BookingListScope = 'upcoming' | 'history'

export type PaginatedClientBookings = {
  items: BookingClientListItem[]
  total: number
  page: number
  page_size: number
}

export type BookingMonthlyRevenue = {
  amount: string
  currency: string
  month: string
  completed_count: number
}

export {
  bookingsMyListApi,
  bookingsMyCreateApi,
  bookingsMyCancelApi,
  bookingsMyRescheduleApi,
} from './client/bookings'

export {
  bookingsListApi,
  bookingsCreateApi,
  bookingsCancelApi,
  bookingsRescheduleApi,
  bookingsMarkAttendanceApi,
  bookingsMonthlyRevenueApi,
} from './master/bookings'
