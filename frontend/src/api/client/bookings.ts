import { apiFetch } from '../client'
import type { Booking, BookingClientListItem, BookingListScope, PaginatedClientBookings } from '../bookings'

export type { Booking, BookingClientListItem, BookingListScope, PaginatedClientBookings }

export async function bookingsMyListApi(params: {
  scope: BookingListScope
  page: number
  page_size: number
}) {
  const q = new URLSearchParams({
    scope: params.scope,
    page: String(params.page),
    page_size: String(params.page_size),
  })
  return apiFetch<PaginatedClientBookings>(`/api/client/bookings?${q}`)
}

export async function bookingsMyCreateApi(body: {
  master_id: string
  service_id: string
  start_at: string
}) {
  return apiFetch<BookingClientListItem>('/api/client/bookings', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function bookingsMyCancelApi(bookingId: string, comment?: string | null) {
  const trimmed = comment?.trim()
  await apiFetch(`/api/client/bookings/${bookingId}/cancel`, {
    method: 'POST',
    body: JSON.stringify(trimmed ? { comment: trimmed } : {}),
  })
}

export async function bookingsMyRescheduleApi(bookingId: string, start_at: string, comment?: string | null) {
  const trimmed = comment?.trim()
  return apiFetch<BookingClientListItem>(`/api/client/bookings/${bookingId}/reschedule`, {
    method: 'POST',
    body: JSON.stringify({
      start_at,
      ...(trimmed ? { comment: trimmed } : {}),
    }),
  })
}
