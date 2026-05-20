import { apiFetch } from '../client'
import type {
  Booking,
  BookingListScope,
  BookingMonthlyRevenue,
  PaginatedBookings,
} from '../bookings'

export type { Booking, BookingListScope, BookingMonthlyRevenue, PaginatedBookings }

export async function bookingsMonthlyRevenueApi() {
  return apiFetch<BookingMonthlyRevenue>('/api/master/bookings/stats/monthly-revenue')
}

export async function bookingsListApi(params: {
  scope: BookingListScope
  page: number
  page_size: number
  client_id?: string
  service_id?: string
}) {
  const q = new URLSearchParams({
    scope: params.scope,
    page: String(params.page),
    page_size: String(params.page_size),
  })
  if (params.client_id) {
    q.set('client_id', params.client_id)
  }
  if (params.service_id) {
    q.set('service_id', params.service_id)
  }
  return apiFetch<PaginatedBookings>(`/api/master/bookings?${q}`)
}

export async function bookingsCreateApi(body: {
  client_id: string
  service_id: string
  start_at: string
}) {
  return apiFetch<Booking>('/api/master/bookings', { method: 'POST', body: JSON.stringify(body) })
}

export async function bookingsCancelApi(id: string, comment?: string | null) {
  const trimmed = comment?.trim()
  await apiFetch(`/api/master/bookings/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify(trimmed ? { comment: trimmed } : {}),
  })
}

export async function bookingsRescheduleApi(id: string, start_at: string, comment?: string | null) {
  const trimmed = comment?.trim()
  return apiFetch<Booking>(`/api/master/bookings/${id}/reschedule`, {
    method: 'POST',
    body: JSON.stringify({
      start_at,
      ...(trimmed ? { comment: trimmed } : {}),
    }),
  })
}

export async function bookingsMarkAttendanceApi(id: string, attended: boolean) {
  return apiFetch<Booking>(`/api/master/bookings/${id}/attendance`, {
    method: 'POST',
    body: JSON.stringify({ attended }),
  })
}
